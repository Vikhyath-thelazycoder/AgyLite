"""Request normalization, phrase matching and change-type classification (spec §15, §54)."""
import re
from functools import lru_cache

# Spec §54: every request after implementation starts is one of these.
CHANGE_TYPES = ("NEW_FEATURE", "FEATURE_CHANGE", "BUG_FIX", "REFACTOR", "SECURITY_CHANGE", "DESIGN_CHANGE",
                "PERFORMANCE_CHANGE", "TESTING_CHANGE", "DOCUMENTATION_CHANGE", "INFRA_CHANGE", "SEO_CHANGE",
                "MEDIA_CHANGE", "OBSERVABILITY_CHANGE", "PLAN_CHANGE")

_QUOTES = str.maketrans({"’": "'", "‘": "'", "“": '"', "”": '"'})

# MP1 F1: URLs and bare domains are masked before keyword matching, so `stripe.com` is not a payment signal.
URL_PLACEHOLDER = "urlref"
_TLDS = "com|io|app|dev|ai|org|net|co|so|sh|xyz|design|studio|tech|site|me|us|uk|de|fr|in"
_FILE_EXTENSIONS = frozenset("py js ts tsx jsx json yaml yml md css html toml lock txt sql sh".split())
_URL = re.compile(r"https?://\S+|www\.\S+|(?<![\w@./-])[a-z0-9-]+(?:\.[a-z0-9-]+)*\.(?:" + _TLDS + r")\b(?:/\S*)?",
                  re.IGNORECASE)
_TRAILING = ".,;:!?)]}'\""


def extract_urls(text: str) -> tuple[str, list[str]]:
    """(text with each URL or bare domain replaced by ` urlref `, the URLs found). A name whose last label is a common
    file extension (`deploy.sh`, `config.yaml`) is a file, not a domain; versions and `node.js` never match."""
    urls = []

    def mask(m):
        url = m.group(0).rstrip(_TRAILING)
        tail = m.group(0)[len(url):]
        host = re.sub(r"^https?://", "", url, flags=re.IGNORECASE).split("/", 1)[0]
        if not m.group(0).lower().startswith(("http", "www.")) and host.rsplit(".", 1)[-1].lower() in _FILE_EXTENSIONS:
            return m.group(0)
        urls.append(url)
        return f" {URL_PLACEHOLDER} {tail}"

    return _URL.sub(mask, text), urls


def normalize(text: str) -> str:
    return " ".join(text.translate(_QUOTES).lower().split())


@lru_cache(maxsize=4096)
def phrase_pattern(phrase: str):
    """Case-insensitive, word-bounded match; spaces match any whitespace; a single word also matches its plural."""
    words = [re.escape(w) for w in normalize(phrase).split()]
    body = r"\s+".join(words)
    if len(words) == 1 and words[0][-1:].isalpha():
        body += r"(?:s|es)?"
    return re.compile(rf"(?<![\w-]){body}(?![\w-])")


def find_phrases(text: str, phrases):
    """The phrases (as written) that occur in normalized `text`."""
    return [p for p in phrases if phrase_pattern(p).search(text)]


def classify_change(text: str, change_cfg, top_domain: str | None):
    """(change type, keyword that decided it or None)."""
    for rx in change_cfg.get("ignore") or []:
        text = re.sub(rx, " ", text)
    for entry in change_cfg.get("order") or []:
        hit = find_phrases(text, entry["keywords"])
        if hit:
            return entry["type"], hit[0]
    by_domain = change_cfg.get("default_by_domain") or {}
    if top_domain in by_domain:
        return by_domain[top_domain], None
    return change_cfg.get("fallback", "FEATURE_CHANGE"), None
