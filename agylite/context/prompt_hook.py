"""UserPromptSubmit hook (MP1 F15, D-048): route every prompt and hand the agent its route with the prompt.

The pilot (AUDIT_REPORT §9) showed the agent often never called Agylite on small, clear tasks (0 calls in the TDD
case), so the SessionStart suggestion alone left it equal to no skill. The hook routes deterministically (no model
call, no network) and prints the route, the load command and the routed L1 cards within `prompt_hook.max_tokens`.
It never blocks a prompt: any error prints nothing.
"""
import hashlib
import json
from pathlib import Path

import yaml

from ..paths import agylite_home, current_bundle, repo_root
from .sections import est_tokens, nbytes

LOAD_REQUEST_CHARS = 200


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
    loader = ContextLoader(project, session_id, current_bundle())
    skills = primary_skill_ids(loader, route.get("whole_skills") or ids[:1], prompt, route.get("skill_hints"))
    # MP3/MP4 Tier 1: agents rarely ran the load command (0 of 37 sessions, then 2 of 3), so the first skill's text
    # arrives with the prompt, whole, when it fits `prompt_hook.primary_skill_max_tokens`; any second skill stays a
    # command. The session cache turns it into a one-line marker on later prompts.
    inline = _inline_skill(loader, skills[0], budgets) if skills else None
    # Option 2 (D-050): when another upstream has a skill for the same job, it rides along whole and one side leads.
    pair = _overlap_partner(loader, skills[0], budgets, root) if inline else None
    if pair:
        skills = [skills[0], pair["partner"]] + [s for s in skills[1:] if s != pair["partner"]]
    rest = skills[(2 if pair else 1):] if inline else skills
    load = (" && ".join(f"agylite skill load {s}" for s in rest) if rest else
            f'agylite context --request "{_quote(prompt)}" ' + " ".join(ids))
    lines = [f"Agylite route: {route['change_type']} · {', '.join(ids)}" + (" (+deps)" if deps else "")]
    also = f" Also load and follow: {load}" if rest else ""
    if pair:
        lines.append(f"The whole skills {pair['lead']} and {pair['other']} follow (one job, two upstreams); follow "
                     f"both before the first edit, and where they disagree follow {pair['lead']}." + also)
    elif inline:
        lines.append(f"The whole skill {skills[0]} follows; follow it before the first edit." + also)
    else:
        lines.append(f"Before the first edit, load the whole skill and follow it: {load}")
    lines.append("Done means: agylite verify passes (tests, types, lint, build).")
    used = est_tokens(nbytes("\n".join(lines)))
    cards, cached = [], []
    caps_dir = (root or repo_root()) / "capabilities"
    for cid in ids:
        path = caps_dir / cid / "CARD.md"
        display = f"capabilities/{cid}/CARD.md"
        if not path.is_file():
            continue
        stat = path.stat()
        if loader.cached(display, stat=stat, sections=["all"]):
            marker = f"(card {cid} already in context)"
            if used + est_tokens(nbytes(marker)) > limit:
                break
            cached.append(cid)
            lines.append(marker)
            used += est_tokens(nbytes(marker))
            continue
        text = path.read_text(encoding="utf-8").rstrip()
        cost = est_tokens(nbytes(text))
        if used + cost > limit:
            break
        loader.record(display, level="L1", stat=stat, sections=["all"], sent_bytes=nbytes(text))
        cards.append(cid)
        lines.append(text)
        used += cost
    if inline:   # outside the card budget: the skills have their own
        texts = [inline, pair["text"]] if pair else [inline]
        if pair and pair["lead"] != skills[0]:
            texts.reverse()   # the leading skill comes first
        lines += [t.rstrip() for t in texts]
    if loader.cache:
        loader.cache.save()
    return {"text": "\n".join(lines) + "\n", "ids": ids, "change_type": route["change_type"], "cards": cards,
            "cached": cached, "skills": skills}


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


def _inline_skill(loader, sid: str, budgets: dict):
    """One skill's whole text (or its cached marker) for the hook; None when it is over the budget or not bundled."""
    from . import levels
    limit = budgets["prompt_hook"].get("primary_skill_max_tokens", 0)
    try:
        entry = levels.find_skill(loader, sid)
        if entry is None or entry["tokens"] > limit:
            return None
        return levels.whole_skill(loader, entry, level="L2")[0]
    except Exception:   # no bundle or an unreadable file: fall back to the load command
        return None


def _overlap_partner(loader, sid: str, budgets: dict, root=None):
    """Option 2 (D-050): {lead, other, partner, text} when skill `sid` is one side of a `skill_overlaps` pair and the
    other side fits `prompt_hook.overlap_skill_max_tokens` (`other` is the skill shown after `lead`'s name); else None."""
    from . import levels
    limit = budgets["prompt_hook"].get("overlap_skill_max_tokens", 0)
    try:
        entry = levels.find_skill(loader, sid)
        pair = levels.overlap_pair(loader, entry, levels.skill_overlaps(root)) if entry else None
        if pair is None:
            return None
        lead, also = pair
        partner = also if lead["path"] == entry["path"] else lead
        if partner["tokens"] > limit:
            return None
        return {"lead": levels.skill_id(lead), "other": levels.skill_id(also), "partner": levels.skill_id(partner),
                "text": levels.whole_skill(loader, partner, level="L2")[0]}
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
