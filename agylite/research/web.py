"""`agylite research read` (MP5 §1.2): a page as text, via Jina Reader (`https://r.jina.ai/<url>`) or, with `--direct`, a
plain HTTP GET and a stdlib HTML→text extraction on this machine (no browser). Private URLs never go to Jina.
Also the helpers the video commands share: subtitle (VTT) de-duplication and the yt-viral swipe-file format."""
import ipaddress
import re
import socket
import urllib.parse
import urllib.request
from html.parser import HTMLParser

JINA = "https://r.jina.ai/"
USER_AGENT = "agylite-research/1.0 (read-only)"
SECRET_PARAMS = re.compile(r"(?:^|[?&;])(?:[\w.-]*?)(token|key|sig)=", re.I)
PRIVATE_SUFFIXES = (".local", ".internal", ".localhost", ".lan", ".home.arpa")
MAX_BYTES = 5_000_000
TIMEOUT = 30


class ReadError(RuntimeError):
    pass


def private_reason(url: str):
    """Why this URL must not be sent to a third party (None when it may): local hosts, private or reserved IPs, internal
    suffixes, and URLs that carry `token=`, `key=` or `sig=`."""
    parts = urllib.parse.urlsplit(url)
    if parts.scheme not in ("http", "https"):
        return f"not an http(s) URL ({parts.scheme or 'no scheme'})"
    host = (parts.hostname or "").lower().rstrip(".")
    if not host:
        return "no host"
    if host == "localhost" or host.endswith(PRIVATE_SUFFIXES):
        return f"local or internal host {host}"
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        ip = None
    if ip is not None and (ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_unspecified):
        return f"private address {host}"
    if "." not in host and ip is None:
        return f"single-label host {host}"
    if SECRET_PARAMS.search(parts.query) or SECRET_PARAMS.search(parts.fragment):
        return "the URL carries a token, key or signature"
    return None


def jina_url(url: str) -> str:
    reason = private_reason(url)
    if reason:
        raise ReadError(f"refusing to send this URL to r.jina.ai: {reason}; use --direct to read it on this machine")
    return JINA + url


def _get(url: str, headers=None) -> tuple:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, **(headers or {})})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            body = resp.read(MAX_BYTES + 1)
            ctype = resp.headers.get("Content-Type", "")
    except (urllib.error.URLError, socket.timeout, ValueError) as exc:
        raise ReadError(f"could not read {url}: {exc}") from exc
    charset = re.search(r"charset=([\w-]+)", ctype)
    text = body[:MAX_BYTES].decode(charset.group(1) if charset else "utf-8", errors="replace")
    return text, ctype


class _Text(HTMLParser):
    """Readable text of a page: drops script/style/nav/header/footer/aside (and ARIA navigation/banner/contentinfo/
    complementary regions), keeps headings, paragraphs and list items; prefers <main>/<article>/role=main when the
    page has one. A tag stack keeps skip/main scopes exact (void elements never open one)."""
    SKIP = {"script", "style", "noscript", "svg", "nav", "header", "footer", "aside", "form", "template", "iframe",
            "button", "select"}
    SKIP_ROLES = {"navigation", "banner", "contentinfo", "complementary", "search", "menu", "menubar"}
    VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}
    BLOCK = {"p", "div", "section", "article", "main", "br", "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6", "pre",
             "blockquote", "table", "ul", "ol", "dd", "dt"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []          # (tag, skip, main)
        self.title = ""
        self._in_title = False
        self.parts = {"all": [], "main": []}

    @property
    def skip(self):
        return any(s for _t, s, _m in self.stack)

    @property
    def main(self):
        return any(m for _t, _s, m in self.stack)

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        role = (a.get("role") or "").lower()
        if tag == "title":
            self._in_title = True
        if tag not in self.VOID:
            self.stack.append((tag, tag in self.SKIP or role in self.SKIP_ROLES or "hidden" in a,
                               tag in ("main", "article") or role == "main"))
        if not self.skip:
            if tag in ("h1", "h2", "h3"):
                self._emit("\n\n" + "#" * int(tag[1]) + " ")
            elif tag == "li":
                self._emit("\n- ")
            elif tag in self.BLOCK:
                self._emit("\n")

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
        if tag in self.BLOCK and not self.skip:
            self._emit("\n")
        for i in range(len(self.stack) - 1, -1, -1):   # close up to the matching open tag (tolerates bad HTML)
            if self.stack[i][0] == tag:
                del self.stack[i:]
                break

    def handle_data(self, data):
        if self._in_title:
            self.title += data
        elif not self.skip:
            self._emit(data)

    def _emit(self, s):
        self.parts["all"].append(s)
        if self.main:
            self.parts["main"].append(s)


def html_to_text(html: str) -> tuple:
    """(title, text)."""
    p = _Text()
    p.feed(html)
    body = "".join(p.parts["main"]) if len("".join(p.parts["main"]).strip()) > 200 else "".join(p.parts["all"])
    lines = [re.sub(r"[ \t\r\f\v]+", " ", l).strip() for l in body.splitlines()]
    lines = [l for l in lines if l not in ("-", "|")]   # empty list items and separators left by dropped links
    text = re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()
    return " ".join(p.title.split()), text


def read(url: str, direct=False) -> dict:
    if direct:
        reason = private_reason(url)
        if reason and reason.startswith("not an http"):
            raise ReadError(reason)
        raw, ctype = _get(url)
        if "html" in ctype or raw.lstrip()[:1] == "<":
            title, text = html_to_text(raw)
        else:
            title, text = "", raw
        return {"url": url, "via": "direct", "title": title, "text": text}
    raw, _ = _get(jina_url(url), headers={"Accept": "text/plain"})
    m = re.match(r"Title:\s*(.*)\n", raw)
    return {"url": url, "via": "r.jina.ai", "title": m.group(1).strip() if m else "", "text": raw}


# ── video helpers ──────────────────────────────────────────────────────────────────────────────────────────────
_CUE_TIME = re.compile(r"^(\d{1,2}:)?\d{2}:\d{2}[.,]\d{3}\s+-->\s+")
_TAG = re.compile(r"<[^>]+>")


def _seconds(stamp: str) -> float:
    parts = stamp.replace(",", ".").split(":")
    return sum(float(x) * 60 ** i for i, x in enumerate(reversed(parts)))


def vtt_lines(vtt: str) -> list:
    """[(seconds, text)] from a (possibly auto-generated) VTT: inline timing tags removed and YouTube's rolling-caption
    repeats dropped — each line is kept once, at the first time it appears."""
    out, seen, start = [], set(), 0.0
    for raw in vtt.splitlines():
        line = raw.strip()
        if not line or line == "WEBVTT" or line.startswith(("Kind:", "Language:", "NOTE", "STYLE")) or line.isdigit():
            continue
        if _CUE_TIME.match(line):
            start = _seconds(line.split("-->")[0].strip())
            continue
        text = " ".join(_TAG.sub("", line).split())
        if text and text not in seen:
            seen.add(text)
            out.append((start, text))
    return out


def stamp(seconds: float) -> str:
    s = int(seconds)
    return f"{s // 3600}:{s % 3600 // 60:02}:{s % 60:02}" if s >= 3600 else f"{s // 60}:{s % 60:02}"


def swipe_rows(listing: dict, channel_url: str) -> list:
    """yt-dlp `--flat-playlist -J` of a channel → yt-viral's input rows {channel,title,views,url,duration}."""
    channel = listing.get("channel") or listing.get("uploader") or listing.get("title") or channel_url
    rows = []
    for e in listing.get("entries") or []:
        if not isinstance(e, dict) or e.get("view_count") is None:
            continue
        url = e.get("url") or (f"https://www.youtube.com/watch?v={e['id']}" if e.get("id") else None)
        if not url:
            continue
        if not url.startswith("http"):
            url = f"https://www.youtube.com/watch?v={url}"
        rows.append({"channel": channel, "title": e.get("title") or "", "views": int(e["view_count"]), "url": url,
                     "duration": int(e.get("duration") or 0)})
    return rows
