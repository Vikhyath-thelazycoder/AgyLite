"""Research runtime (MP5 §1.2): an isolated venv `runtimes/research-<lock>` with the pinned Agent-Reach package and its
tested dependency set (constraints.txt), plus opt-in extras. `agylite research` calls only the allow-listed tools below,
never `agent-reach` subcommands, so Agent-Reach's MCP, Exa/mcporter, OpenCLI, browser-cookie, transcription and
Chinese-platform code (shipped inside the pip package) never runs.

| command        | tool                                   | egress            | needs                 |
| read           | r.jina.ai, or --direct HTTP GET        | r.jina.ai / site  | —                     |
| rss            | feedparser (runtime venv)              | the feed          | runtime               |
| video …        | yt-dlp --skip-download                 | youtube.com       | runtime               |
| github         | gh search repos|code|issues            | github.com        | gh CLI                |
| x              | twitter search (twitter-cli 0.8.5)     | x.com             | `enable x`            |
| reddit         | rdt search / rdt read (rdt-cli, pinned)| reddit.com        | `enable reddit`       |

Read-only: no write subcommand of twitter-cli or rdt-cli is reachable. Browser cookies are never read: the extras are
installed without `browser-cookie3`, children get a private empty HOME (deleted afterwards) and a PATH without `uv`,
and yt-dlp runs with `--no-cookies --no-cookies-from-browser --ignore-config`. Credentials reach only the child of
the one command that needs them. At most 1 call per second per platform; X ≤ 20 and Reddit ≤ 25 results per call.
"""
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from ..research import secrets
from . import venv as pyvenv

AGENT_REACH = "Panniantong/Agent-Reach"
CORE = ["requests", "feedparser", "python-dotenv", "loguru", "pyyaml", "rich", "yt-dlp[default]"]
EXTRAS = {
    "x": {"pkg": "twitter-cli==0.8.5", "bin": "twitter",
          "deps": ["click>=8.0", "rich>=13.0", "PyYAML>=6.0", "curl_cffi>=0.7", "xclienttransaction>=1.0.1",
                   "beautifulsoup4>=4.12"]},
    "reddit": {"pkg": "rdt-cli @ git+https://github.com/public-clis/rdt-cli.git@5e4fb3720d5c174e976cd425ccc3b879d52cac66",
               "bin": "rdt", "deps": ["click>=8.0", "rich>=13.0", "httpx>=0.27", "pyyaml>=6.0"]},
}
FORBIDDEN_PACKAGES = ("browser-cookie3", "browser_cookie3", "playwright", "mcp")
LIMITS = {"x": 20, "reddit": 25}
GH_TYPES = {"repos": ["repos", "--sort", "stars"], "code": ["code"], "issues": ["issues"]}
GH_FIELDS = {"repos": "fullName,description,stargazersCount,updatedAt,url",
             "code": "path,repository,url", "issues": "title,repository,state,updatedAt,url"}
YTDLP_SAFE = ["--ignore-config", "--no-cookies", "--no-cookies-from-browser", "--no-warnings", "--skip-download"]
SECRET_ENV = re.compile(r"(KEY|TOKEN|SECRET|PASSWORD|CREDENTIAL|COOKIE|SESSION)", re.I)
TIMEOUT = 300


class ResearchError(RuntimeError):
    pass


# ── runtime ────────────────────────────────────────────────────────────────────────────────────────────────────
def pin() -> str:
    from ..bundle.rules import evidence_dir, load_yaml
    return load_yaml(evidence_dir() / "upstream-staging-snapshot.yaml")["snapshots"]["agentreach"]["head"]


def constraints(bundle_dir) -> Path | None:
    p = Path(bundle_dir) / "files" / "agentreach" / "constraints.txt" if bundle_dir else None
    return p if p and p.is_file() else None


def lock(bundle_dir) -> str:
    c = constraints(bundle_dir)
    h = hashlib.sha256(pin().encode() + b"\0" + (c.read_bytes() if c else b""))
    return h.hexdigest()[:12]


def runtime_dir(home, bundle_dir) -> Path:
    return Path(home) / "runtimes" / f"research-{lock(bundle_dir)}"


def tool(home, bundle_dir, name) -> Path:
    return pyvenv.bin_path(runtime_dir(home, bundle_dir) / "venv", name)


def _pip(py, *args):
    p = subprocess.run([str(py), "-m", "pip", "install", "-q", "--disable-pip-version-check", *args],
                       capture_output=True, text=True)
    if p.returncode:
        raise ResearchError(f"pip install failed: {(p.stderr or p.stdout).strip()[-600:]}")


def _purge_forbidden(py) -> list:
    """Remove any browser-cookie/MCP/browser package a dependency pulled in; returns what was removed."""
    removed = []
    for name in FORBIDDEN_PACKAGES:
        if subprocess.run([str(py), "-m", "pip", "show", "-q", name], capture_output=True).returncode == 0:
            subprocess.run([str(py), "-m", "pip", "uninstall", "-y", "-q", name], capture_output=True)
            removed.append(name)
    return removed


def cookie_reader_absent(py) -> bool:
    return subprocess.run([str(py), "-I", "-c", "import browser_cookie3"], capture_output=True).returncode != 0


def install(home, bundle_dir, log=print) -> dict:
    """Venv + Agent-Reach at the audited commit (--no-deps) + its tested dependencies (-c constraints.txt)."""
    c = constraints(bundle_dir)
    if c is None:
        raise ResearchError("no active bundle with files/agentreach/constraints.txt (run `agylite bundle build`)")
    final = runtime_dir(home, bundle_dir)
    if (final / "runtime.json").is_file():
        return json.loads((final / "runtime.json").read_text(encoding="utf-8"))
    shutil.rmtree(final, ignore_errors=True)
    final.mkdir(parents=True)
    start = time.perf_counter()
    try:
        subprocess.run([sys.executable, "-m", "venv", str(final / "venv")], check=True, capture_output=True)
        py = pyvenv.bin_path(final / "venv", "python")
        log(f"installing research runtime {final.name} (agent-reach @ {pin()[:7]}, constraints.txt)…")
        _pip(py, "--no-deps", f"agent-reach @ git+https://github.com/{AGENT_REACH}.git@{pin()}")
        _pip(py, "-c", str(c), *CORE)
        removed = _purge_forbidden(py)
        version = subprocess.run([str(tool(home, bundle_dir, "yt-dlp")), "--version"], capture_output=True,
                                 text=True).stdout.strip()
        info = {"runtime": "research", "lock": final.name.split("-", 1)[1], "agent_reach": pin(),
                "yt_dlp": version, "extras": [], "removed": removed, "python": sys.version.split()[0],
                "installed": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "install_seconds": round(time.perf_counter() - start, 1)}
        _write_info(final, info)
        return info
    except BaseException:
        shutil.rmtree(final, ignore_errors=True)
        raise


def _write_info(final, info):
    from ..isolation import atomic
    atomic.write_text(final / "runtime.json", json.dumps(info, indent=1) + "\n")


def info(home, bundle_dir) -> dict | None:
    p = runtime_dir(home, bundle_dir) / "runtime.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else None


def add_extra(home, bundle_dir, channel, log=print) -> dict:
    """Install twitter-cli or rdt-cli into the runtime without browser-cookie3 (explicit opt-in only)."""
    meta = info(home, bundle_dir)
    if meta is None:
        meta = install(home, bundle_dir, log=log)
    if channel in meta.get("extras", []):
        return meta
    spec = EXTRAS[channel]
    py = pyvenv.bin_path(runtime_dir(home, bundle_dir) / "venv", "python")
    log(f"adding {spec['pkg'].split(' @ ')[0]} to the research runtime (without browser-cookie3)…")
    _pip(py, "--no-deps", spec["pkg"])
    _pip(py, *spec["deps"])
    removed = _purge_forbidden(py)
    if not cookie_reader_absent(py):
        raise ResearchError("browser-cookie3 is importable in the research runtime; refusing to enable the channel")
    meta["extras"] = sorted({*meta.get("extras", []), channel})
    meta["removed"] = sorted({*meta.get("removed", []), *removed})
    _write_info(runtime_dir(home, bundle_dir), meta)
    return meta


def health(home, bundle_dir) -> dict:
    if constraints(bundle_dir) is None:
        return {"runtime": "research", "status": "no-bundle", "reason": "no active bundle with files/agentreach"}
    meta = info(home, bundle_dir)
    if meta is None:
        return {"runtime": "research", "status": "not-installed", "reason": "run `agylite runtime install research`"}
    return {"runtime": "research", "status": "ready", "yt_dlp": meta.get("yt_dlp"), "extras": meta.get("extras", []),
            "path": str(runtime_dir(home, bundle_dir))}


# ── argv (the allow-list) ──────────────────────────────────────────────────────────────────────────────────────
def video_argv(ytdlp, url, out_dir, *, subs=False, meta=False, comments=0) -> list:
    if subs:
        return [str(ytdlp), *YTDLP_SAFE, "--write-subs", "--write-auto-subs", "--sub-langs", "en.*,en",
                "--sub-format", "vtt", "-o", str(Path(out_dir) / "%(id)s.%(ext)s"), url]
    if comments:
        return [str(ytdlp), *YTDLP_SAFE, "--write-comments", "--dump-single-json", "--extractor-args",
                f"youtube:max_comments={int(comments)},all,0,0;comment_sort=top", url]
    return [str(ytdlp), *YTDLP_SAFE, "--dump-single-json", url]


def video_search_argv(ytdlp, query, n) -> list:
    return [str(ytdlp), *YTDLP_SAFE, "--flat-playlist", "--dump-single-json", f"ytsearch{int(n)}:{query}"]


def channel_argv(ytdlp, url, n) -> list:
    if re.search(r"youtube\.com/(@[^/]+|c/[^/]+|channel/[^/]+|user/[^/]+)/?$", url):
        url = url.rstrip("/") + "/videos"
    return [str(ytdlp), *YTDLP_SAFE, "--flat-playlist", "--dump-single-json", "--playlist-end", str(int(n)),
            "--extractor-args", "youtubetab:approximate_date", url]


def github_argv(gh, query, kind="repos", n=10) -> list:
    if kind not in GH_TYPES:
        raise ResearchError(f"github --type must be one of {', '.join(GH_TYPES)}")
    return [str(gh), "search", *GH_TYPES[kind], query, "--limit", str(int(n)), "--json", GH_FIELDS[kind]]


def x_argv(twitter, query, n=10) -> list:
    return [str(twitter), "search", query, "--max", str(min(int(n), LIMITS["x"])), "--json"]


def reddit_argv(rdt, query=None, *, sub=None, n=10, read=None) -> list:
    if read:
        return [str(rdt), "read", read, "--limit", str(min(int(n), LIMITS["reddit"])), "--json"]
    return [str(rdt), "search", query, *(["--subreddit", sub] if sub else []),
            "--limit", str(min(int(n), LIMITS["reddit"])), "--json"]


# ── running ────────────────────────────────────────────────────────────────────────────────────────────────────
def tmp_dir(home) -> Path:
    d = Path(home) / "tmp" / "research"
    d.mkdir(parents=True, exist_ok=True)
    return d


def child_env(home, bundle_dir, private_home: Path, extra=None, path_extra=()) -> dict:
    """A minimal environment: the runtime's bin first, system bins, a private empty HOME, no inherited secrets."""
    venv_bin = str(pyvenv.bin_path(runtime_dir(home, bundle_dir) / "venv", "python").parent)
    keep = {k: v for k, v in os.environ.items()
            if k in ("LANG", "LC_ALL", "LC_CTYPE", "TZ", "TERM", "SSL_CERT_FILE", "REQUESTS_CA_BUNDLE",
                     "HTTPS_PROXY", "HTTP_PROXY", "NO_PROXY", "https_proxy", "http_proxy", "no_proxy")
            and not SECRET_ENV.search(k)}
    keep.update(HOME=str(private_home), PATH=os.pathsep.join([venv_bin, *path_extra, "/usr/bin", "/bin"]),
                XDG_CONFIG_HOME=str(private_home / ".config"), XDG_CACHE_HOME=str(private_home / ".cache"),
                PYTHONNOUSERSITE="1")
    keep.update(extra or {})
    return keep


def pace(home, platform, min_gap=1.0):
    stamp = tmp_dir(home) / f".last-{platform}"
    try:
        wait = min_gap - (time.time() - stamp.stat().st_mtime)
    except OSError:
        wait = 0
    if wait > 0:
        time.sleep(wait)
    stamp.touch()


def run_tool(home, bundle_dir, argv, platform, *, extra_env=None, files=None, path_extra=(), timeout=TIMEOUT):
    """Run one allow-listed tool with a private HOME (deleted afterwards). `files` are written into that HOME first
    (e.g. rdt-cli's credential file) with mode 0600."""
    pace(home, platform)
    base = secrets.secrets_dir(home) if files else tmp_dir(home)   # a HOME holding credentials lives under secrets/
    base.mkdir(parents=True, exist_ok=True)
    os.chmod(base, 0o700)
    with tempfile.TemporaryDirectory(prefix="home-", dir=base) as d:
        private = Path(d)
        os.chmod(private, 0o700)
        for rel, text in (files or {}).items():
            target = private / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(text)
        env = child_env(home, bundle_dir, private, extra_env, path_extra)
        try:
            return subprocess.run([str(a) for a in argv], cwd=private, env=env, capture_output=True, text=True,
                                  timeout=timeout)
        except subprocess.TimeoutExpired as exc:
            raise ResearchError(f"{Path(argv[0]).name} timed out after {timeout}s") from exc


def require_runtime(home, bundle_dir):
    if info(home, bundle_dir) is None:
        raise ResearchError("the research runtime is not installed: run `agylite runtime install research`")


def rss(home, bundle_dir, feed, limit=10) -> list:
    require_runtime(home, bundle_dir)
    py = pyvenv.bin_path(runtime_dir(home, bundle_dir) / "venv", "python")
    script = ("import json,sys,feedparser;f=feedparser.parse(sys.argv[1]);"
              "print(json.dumps({'title':f.feed.get('title',''),'error':str(f.get('bozo_exception') or '') if not f.entries else '',"
              "'entries':[{'title':e.get('title',''),'link':e.get('link',''),'published':e.get('published',''),"
              "'summary':(e.get('summary') or '')[:400]} for e in f.entries[:int(sys.argv[2])]]}))")
    p = run_tool(home, bundle_dir, [py, "-I", "-c", script, feed, str(int(limit))], "rss")
    if p.returncode:
        raise ResearchError(f"rss failed: {(p.stderr or p.stdout).strip()[-300:]}")
    return json.loads(p.stdout)


def video(home, bundle_dir, url, *, subs=False, meta=False, comments=0) -> dict:
    from ..research import web
    require_runtime(home, bundle_dir)
    ytdlp = tool(home, bundle_dir, "yt-dlp")
    out_dir = Path(tempfile.mkdtemp(prefix="video-", dir=tmp_dir(home)))
    result = {"url": url, "files": []}
    if subs:
        p = run_tool(home, bundle_dir, video_argv(ytdlp, url, out_dir, subs=True), "youtube")
        vtts = sorted(out_dir.glob("*.vtt"), key=lambda f: (".en." not in f.name, f.name))
        if not vtts:
            result["subs_error"] = (p.stderr or p.stdout).strip()[-300:] or "no subtitles"
        else:
            lines = web.vtt_lines(vtts[0].read_text(encoding="utf-8", errors="replace"))
            text_path = out_dir / (vtts[0].stem + ".txt")
            text_path.write_text("".join(f"[{web.stamp(t)}] {s}\n" for t, s in lines), encoding="utf-8")
            result.update(transcript=[{"t": round(t, 1), "at": web.stamp(t), "text": s} for t, s in lines],
                          subtitle_file=vtts[0].name)
            result["files"] += [str(vtts[0]), str(text_path)]
    if meta or comments:
        p = run_tool(home, bundle_dir, video_argv(ytdlp, url, out_dir, comments=comments), "youtube")
        if p.returncode:
            result["meta_error"] = (p.stderr or p.stdout).strip()[-300:]
        else:
            data = json.loads(p.stdout)
            (out_dir / "info.json").write_text(json.dumps(data), encoding="utf-8")
            result["files"].append(str(out_dir / "info.json"))
            result["meta"] = {k: data.get(k) for k in ("id", "title", "channel", "uploader", "upload_date", "duration",
                                                        "view_count", "like_count", "comment_count", "description",
                                                        "tags", "webpage_url")}
            result["meta"]["chapters"] = [{"at": web.stamp(c.get("start_time") or 0), "title": c.get("title")}
                                          for c in data.get("chapters") or []]
            if comments:
                result["comments"] = [{"author": c.get("author"), "likes": c.get("like_count"), "text": c.get("text")}
                                      for c in (data.get("comments") or [])[: int(comments)]]
    return result


def video_search(home, bundle_dir, query, n=5) -> list:
    require_runtime(home, bundle_dir)
    p = run_tool(home, bundle_dir, video_search_argv(tool(home, bundle_dir, "yt-dlp"), query, n), "youtube")
    if p.returncode:
        raise ResearchError(f"video-search failed: {(p.stderr or p.stdout).strip()[-300:]}")
    data = json.loads(p.stdout)
    return [{"title": e.get("title"), "channel": e.get("channel") or e.get("uploader"), "views": e.get("view_count"),
             "duration": e.get("duration"), "url": e.get("url") or f"https://www.youtube.com/watch?v={e.get('id')}"}
            for e in data.get("entries") or []]


def channel(home, bundle_dir, url, n=30) -> dict:
    require_runtime(home, bundle_dir)
    p = run_tool(home, bundle_dir, channel_argv(tool(home, bundle_dir, "yt-dlp"), url, n), "youtube")
    if p.returncode:
        raise ResearchError(f"channel failed: {(p.stderr or p.stdout).strip()[-300:]}")
    return json.loads(p.stdout)


def github(home, bundle_dir, query, kind="repos", n=10) -> list:
    gh = shutil.which("gh")
    if not gh:
        raise ResearchError("missing gh: install the GitHub CLI and run `gh auth login`, or read repos with "
                            "`agylite research read https://github.com/<owner>/<repo>`")
    pace(home, "github")
    p = subprocess.run(github_argv(gh, query, kind, n), capture_output=True, text=True, timeout=TIMEOUT)
    if p.returncode:
        raise ResearchError(f"gh search failed: {(p.stderr or p.stdout).strip()[-300:]}")
    return json.loads(p.stdout or "[]")


def x(home, bundle_dir, query, n=10):
    creds = secrets.load(home, "x")
    if not creds or "x" not in (info(home, bundle_dir) or {}).get("extras", []):
        raise ResearchError("x is disabled: the owner enables it once with `agylite research enable x`")
    argv = x_argv(tool(home, bundle_dir, "twitter"), query, n)
    return run_tool(home, bundle_dir, argv, "x",
                    extra_env={"TWITTER_AUTH_TOKEN": creds["auth_token"], "TWITTER_CT0": creds["ct0"]})


def reddit(home, bundle_dir, query=None, *, sub=None, n=10, read=None):
    creds = secrets.load(home, "reddit")
    if not creds or "reddit" not in (info(home, bundle_dir) or {}).get("extras", []):
        raise ResearchError("reddit is disabled: the owner enables it once with `agylite research enable reddit`")
    credential = json.dumps({"cookies": {"reddit_session": creds["reddit_session"]}, "source": "agylite",
                             "saved_at": time.time(), "username": None, "modhash": None, "last_verified_at": None})
    argv = reddit_argv(tool(home, bundle_dir, "rdt"), query, sub=sub, n=n, read=read)
    return run_tool(home, bundle_dir, argv, "reddit", files={".config/rdt-cli/credential.json": credential})


def doctor(home, bundle_dir) -> dict:
    """Only the allowed channels (never upstream `agent-reach doctor`, which probes excluded channels)."""
    meta = info(home, bundle_dir)
    rt = "ok" if meta else "missing runtime (`agylite runtime install research`)"
    rows = {"web": "ok (Jina Reader r.jina.ai, or --direct on this machine)", "rss": rt,
            "video": f"ok (yt-dlp {meta.get('yt_dlp')})" if meta else rt,
            "github": f"ok ({shutil.which('gh')})" if shutil.which("gh") else "missing gh (GitHub CLI)"}
    for ch, note in (("x", ""), ("reddit", " (rdt-cli unmaintained upstream since 2026-03)")):
        state = secrets.status(home, ch)
        installed = meta is not None and ch in meta.get("extras", [])
        rows[ch] = ("enabled" if state.startswith("enabled") and installed else "disabled") + note
    if meta:
        py = pyvenv.bin_path(runtime_dir(home, bundle_dir) / "venv", "python")
        rows["browser cookies"] = ("never read (browser-cookie3 not installed)" if cookie_reader_absent(py)
                                   else "WARNING: browser-cookie3 importable")
    return rows
