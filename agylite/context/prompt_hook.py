"""UserPromptSubmit hook (MP1 F15, D-048): route every prompt and hand the agent its route with the prompt.

The pilot (AUDIT_REPORT §9) showed the agent often never called Agylite on small, clear tasks (0 calls in the TDD
case), so the SessionStart suggestion alone left it equal to no skill. The hook routes deterministically (no model
call, no network) and prints the route, the load command and the routed L1 cards within `prompt_hook.max_tokens`.
It never blocks a prompt: any error prints nothing.
"""
import fnmatch
import hashlib
import json
from pathlib import Path

import yaml

from ..paths import agylite_home, current_bundle, repo_root
from .sections import est_tokens, nbytes

LOAD_REQUEST_CHARS = 200
PONYTAIL_OFF = ("Ponytail lite is off for this task (creative work): its least-code rules and closing lines do not "
                "apply; do every iteration and quality step the skill asks for, and keep refining until it says stop.")


def load_discipline(root: Path | None = None) -> dict:
    path = (root or repo_root()) / "config" / "discipline.yaml"
    return yaml.safe_load(path.read_text(encoding="utf-8")) if path.is_file() else {}


def is_followup(prompt: str, cfg: dict) -> bool:
    """A short follow-up (`yes`, `go on`, ≤ N words) carries no new task; the earlier route still applies."""
    words = prompt.split()
    hook = cfg.get("prompt_hook_followups") or {}
    if len(words) <= int(hook.get("max_words", 3)):
        return True
    return prompt.strip().lower().strip(".!? ") in {w.lower() for w in hook.get("phrases") or []}


def _quote(text: str) -> str:
    return text[:LOAD_REQUEST_CHARS].replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")


def build(prompt: str, session_id: str | None, cwd: str | None, host: str, *, budgets: dict, root=None) -> str:
    """The text to inject for one prompt ("" when nothing should be injected)."""
    from ..events import emit
    from ..project.identity import detect

    cfg = load_discipline(root)
    if str(cfg.get("prompt_hook", "on")).lower() in ("off", "false") or not prompt.strip():
        return ""
    if prompt.lstrip().startswith("/") or is_followup(prompt, cfg):
        return ""
    project = detect(Path(cwd) if cwd else None)
    meta = {"prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest()[:16], "length": len(prompt)}
    hook = compose(prompt, project, budgets, root=root, session_id=session_id)
    if hook is None:
        emit(project, "ROUTE_UNMATCHED", session_id=session_id, host=host, details=meta)
        return ""
    emit(project, "PROMPT_ROUTED", session_id=session_id, host=host, capabilities=hook["ids"],
         est_tokens=est_tokens(nbytes(hook["text"])),
         details={**meta, "change_type": hook["change_type"], "cards": hook["cards"], "cached_cards": hook["cached"],
                  "skills": hook["skills"]})
    _mark_fired(host)
    return hook["text"]


def compose(prompt: str, project, budgets: dict, *, root=None, session_id=None):
    """The hook's text for one routed prompt, with no events and no fired marker (the token report measures it);
    None when the route is unmatched. With a session, the cards sent are recorded in its context cache."""
    from ..routing import Router
    from .loader import ContextLoader
    from ..cli import _facts   # the same project facts `agylite route` uses
    route = Router(root).route(prompt, project=_facts(project))
    if route["unmatched"]:
        return None
    ids = [c["id"] for c in route["capabilities"]]
    deps = [d["id"] for d in route["dependencies"]]
    limit = budgets["prompt_hook"]["max_tokens"]
    # C1-2 (Step 3 part 2): Claude Code saves hook output over ≈ 10,000 chars to a file the agent may never open, so
    # the whole hook stays within `prompt_hook.max_chars`: lead skill first, its partner if it still fits, cards last.
    cap = budgets["prompt_hook"]["max_chars"]
    lead_cid = ((route.get("whole_skills") or ids)[:1] or [None])[0]
    exempt = lead_cid and any(fnmatch.fnmatchcase(lead_cid, g)
                              for g in load_discipline(root).get("ponytail_exempt") or [])
    loader = ContextLoader(project, session_id, current_bundle())
    # C1-5 / C1-11: one skill leads; only its overlap partner joins it (a 3rd skill made the largest payloads).
    skills = primary_skill_ids(loader, (route.get("whole_skills") or ids)[:1], prompt, route.get("skill_hints"))
    # MP3/MP4 Tier 1: agents rarely ran the load command (0 of 37 sessions, then 2 of 3), so the first skill's text
    # arrives with the prompt, whole; the session cache turns it into a one-line marker on later prompts.
    lead = _inline_skill(loader, skills[0]) if skills else None
    # Option 2 (D-050): when another upstream has a skill for the same job, it rides along whole and one side leads.
    pair = _overlap_partner(loader, skills[0], root) if lead else None

    def head(inline, pair):
        out = [f"Agylite route: {route['change_type']} · {', '.join(ids)}" + (" (+deps)" if deps else "")]
        if exempt:
            out.append(PONYTAIL_OFF)
        if pair:
            out.append(f"The whole skills {pair['lead']} and {pair['other']} follow (one job, two upstreams); follow "
                       f"both before the first edit, and where they disagree follow {pair['lead']}.")
        elif inline:
            out.append(f"The whole skill {skills[0]} follows; follow it before the first edit.")
        elif lead:   # too big to ride along: one Read of the file, not a CLI call agents skip
            out.append(f"Before the first edit, read the whole skill {skills[0]} and follow it: {lead['path']}")
        elif skills:
            out.append(f"Before the first edit, load the whole skill and follow it: agylite skill load {skills[0]}")
        else:
            out.append("Before the first edit, load the whole skill and follow it: "
                       f'agylite context --request "{_quote(prompt)}" ' + " ".join(ids))
        out.append("Done means: agylite verify passes (tests, types, lint, build).")
        return out

    def size(lines, texts=()):
        return len("\n".join(list(lines) + [t.rstrip() for t in texts]) + "\n")

    if pair and size(head(lead, pair), [lead["text"], pair["text"]]) > cap:
        loader.forget(pair["path"])
        pair = None
    inline = lead if lead and size(head(lead, None), [lead["text"]]) <= cap else None
    if lead and not inline:
        loader.forget(lead["key"])
    lines = head(inline, pair)
    texts = ([] if not inline else [inline["text"], pair["text"]] if pair else [inline["text"]])
    if pair and pair["lead"] != skills[0]:
        texts.reverse()   # the leading skill comes first
    used = est_tokens(nbytes("\n".join(lines)))
    left = cap - size(lines, texts)   # cards fit both their token budget and what the skills leave of the cap
    cards, cached = [], []
    caps_dir = (root or repo_root()) / "capabilities"
    for cid in ids:
        path = caps_dir / cid / "CARD.md"
        display = f"capabilities/{cid}/CARD.md"
        if not path.is_file():
            continue
        stat = path.stat()
        if loader.cached(display, stat=stat, sections=["all"]):
            text = f"(card {cid} already in context)"
            if used + est_tokens(nbytes(text)) > limit or len(text) + 1 > left:
                break
            cached.append(cid)
        else:
            text = path.read_text(encoding="utf-8").rstrip()
            if used + est_tokens(nbytes(text)) > limit or len(text) + 1 > left:
                break
            loader.record(display, level="L1", stat=stat, sections=["all"], sent_bytes=nbytes(text))
            cards.append(cid)
        lines.append(text)
        used += est_tokens(nbytes(text))
        left -= len(text) + 1
    lines += [t.rstrip() for t in texts]
    if loader.cache:
        loader.cache.save()
    return {"text": "\n".join(lines) + "\n", "ids": ids, "change_type": route["change_type"], "cards": cards,
            "cached": cached, "skills": skills + ([pair["partner"]] if pair else [])}


def primary_skill_ids(loader, cids, query, hints=None) -> list:
    """Plan B: the skill ids (`<upstream>/<name>`) of these capabilities' primary skills, from the bundle index. A
    route's skill hint (D-050) leads the capability's sources_priority."""
    from . import levels
    hints = hints or {}
    try:
        prios = levels.source_priorities()
        out = []
        for cid in cids:
            prio = ([hints[cid]] if cid in hints else []) + list(prios.get(cid, ()))
            entry = levels.primary_skill(levels.capability_entries(loader, cid, prio), query, prio)
            if entry is not None and entry["kind"] == "skill":
                out.append(levels.skill_id(entry))
        return out
    except Exception:   # no bundle yet: fall back to the context command
        return []


def _inline_skill(loader, sid: str):
    """{key, path, text}: one skill's whole text (or its cached marker) for the hook; None when it is not bundled."""
    from . import levels
    try:
        entry = levels.find_skill(loader, sid)
        if entry is None:
            return None
        return {"key": entry["path"], "path": str(loader.source(entry)),
                "text": levels.whole_skill(loader, entry, level="L2")[0]}
    except Exception:   # no bundle or an unreadable file: fall back to the load command
        return None


def _overlap_partner(loader, sid: str, root=None):
    """Option 2 (D-050): {lead, other, partner, path, text} when skill `sid` is one side of a `skill_overlaps` pair
    (`other` is the skill shown after `lead`'s name, `path` the partner's bundle path); else None."""
    from . import levels
    try:
        entry = levels.find_skill(loader, sid)
        pair = levels.overlap_pair(loader, entry, levels.skill_overlaps(root)) if entry else None
        if pair is None:
            return None
        lead, also = pair
        partner = also if lead["path"] == entry["path"] else lead
        return {"lead": levels.skill_id(lead), "other": levels.skill_id(also), "partner": levels.skill_id(partner),
                "path": partner["path"], "text": levels.whole_skill(loader, partner, level="L2")[0]}
    except Exception:   # no bundle or an unreadable file: the first skill alone
        return None


def _mark_fired(host: str):
    """`agylite doctor` reports when the hook last fired (one small file, no event-log scan)."""
    from datetime import datetime, timezone

    from ..isolation import atomic
    atomic.write_text(agylite_home() / "hosts" / "prompt-hook.json",
                      json.dumps({"host": host, "last_fired": datetime.now(timezone.utc).isoformat()}))


def run(stdin_text: str, host: str) -> str:
    """Hook entry: parse Claude Code's UserPromptSubmit input (`prompt`, `session_id`, `cwd`); never raise."""
    try:
        data = json.loads(stdin_text or "")
        if not isinstance(data, dict) or not isinstance(data.get("prompt"), str):
            return ""
        from .budget import load_budgets
        return build(data["prompt"], data.get("session_id"), data.get("cwd"), host, budgets=load_budgets())
    except Exception:   # the hook must never break or block a prompt
        return ""
