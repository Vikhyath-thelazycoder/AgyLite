"""Request normalization, phrase matching and change-type classification (spec §15, §54)."""
import re
from functools import lru_cache

# Spec §54: every request after implementation starts is one of these.
CHANGE_TYPES = ("NEW_FEATURE", "FEATURE_CHANGE", "BUG_FIX", "REFACTOR", "SECURITY_CHANGE", "DESIGN_CHANGE",
                "PERFORMANCE_CHANGE", "TESTING_CHANGE", "DOCUMENTATION_CHANGE", "INFRA_CHANGE", "SEO_CHANGE",
                "MEDIA_CHANGE", "OBSERVABILITY_CHANGE", "PLAN_CHANGE")

_QUOTES = str.maketrans({"’": "'", "‘": "'", "“": '"', "”": '"'})


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
