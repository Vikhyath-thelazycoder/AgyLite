"""Requirements question engine (spec §53, §19.3): ask only what materially changes implementation.

BLOCKING before IMPORTANT/OPTIONAL; no OPTIONAL question while a BLOCKING one is open; never ask what the project's
manifests already answer (inferred) or what was answered before.
"""
from pathlib import Path

import yaml

from ..paths import repo_root
from ..routing.classify import find_phrases, normalize

PRIORITIES = ("BLOCKING", "IMPORTANT", "OPTIONAL")


def load_bank(root: Path | None = None):
    with open((root or repo_root()) / "config" / "questions.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def validate_bank(bank):
    p, seen = [], set()
    for q in bank.get("questions") or []:
        qid = q.get("id")
        if not qid or qid in seen:
            p.append(f"question {qid!r}: id missing or duplicated")
        seen.add(qid)
        if q.get("priority") not in PRIORITIES:
            p.append(f"{qid}: priority must be one of {PRIORITIES}")
        if not q.get("question") or not q.get("affects"):
            p.append(f"{qid}: needs question text and `affects` (what the answer changes)")
        if not q.get("new_project") and not q.get("ask_when") and not q.get("ask_when_capability"):
            p.append(f"{qid}: needs new_project: true, ask_when keywords or ask_when_capability")
    return p


def inferred(bank, stack):
    """{question id: inferred answer} from detected stack tags."""
    out = {}
    tags = set(stack or ())
    for q in bank.get("questions") or []:
        hit = [t for t in q.get("inferable_from") or [] if t in tags]
        if hit:
            out[q["id"]] = ", ".join(hit)
    return out


def next_questions(bank, request, *, stage, answers=None, stack=(), limit=5, capabilities=()):
    """The questions to ask now, highest priority first; returns (questions, skipped {id: reason}). A question with
    `ask_when_capability` applies when the request's route selects one of them (MP4 §3.2: DESIGN.md approval)."""
    text = normalize(request or "")
    answers = answers or {}
    known = inferred(bank, stack)
    open_qs, skipped = [], {}
    for q in bank.get("questions") or []:
        applies = ((q.get("new_project") and stage == "new") or bool(find_phrases(text, q.get("ask_when") or []))
                   or bool(set(q.get("ask_when_capability") or []) & set(capabilities)))
        if not applies:
            continue
        if q["id"] in answers:
            skipped[q["id"]] = "answered"
        elif q["id"] in known:
            skipped[q["id"]] = f"inferred from the project ({known[q['id']]})"
        else:
            open_qs.append(q)
    blocking = [q for q in open_qs if q["priority"] == "BLOCKING"]
    if blocking:
        chosen = blocking
        for q in open_qs:
            if q["priority"] != "BLOCKING":
                skipped[q["id"]] = "deferred until blocking questions are answered"
    else:
        chosen = sorted(open_qs, key=lambda q: PRIORITIES.index(q["priority"]))
    for q in chosen[limit:]:
        skipped[q["id"]] = "over the per-turn limit"
    return [{"id": q["id"], "priority": q["priority"], "question": q["question"], "affects": q["affects"]}
            for q in chosen[:limit]], skipped
