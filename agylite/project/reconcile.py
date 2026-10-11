"""Living-plan reconciliation (spec §21, §56): place a change in the right phase of the ONE implementation plan.

`reconcile()` = classify (router) → locate phase → impact (§55) → add the task to that phase's table → append the
change history → rebuild the index → update state. It never creates a separate mini-plan file.
"""
import re
from datetime import date

from ..isolation import atomic
from ..isolation.locks import project_lock
from ..routing.fallback_bm25 import tokenize
from ..routing.rules import _glob_match
from . import plan_index
from .change import impact as change_impact
from .lifecycle import DONE_STATES, check_transition
from .state import checked, read_yaml, record_verification, update_state, write_yaml

GENERIC = set(tokenize("add build create make fix update change new feature implement improve support integrate "
                       "page app application system module flow please also want need let get set"))
HISTORY_HEADING = "## Change history"
# Spec §30 lifecycle events emitted when a task/phase status changes.
STATUS_EVENTS = {"IN_PROGRESS": "TASK_STARTED", "BLOCKED": "TASK_BLOCKED", "COMPLETED": "TASK_COMPLETED",
                 "READY_FOR_VERIFICATION": "TASK_READY_FOR_VERIFICATION", "VERIFIED": "TASK_VERIFIED"}
STATUS_META = re.compile(r"(Status:[ \t]*)([A-Z_]+)")
EVIDENCE_META = re.compile(r"(Evidence:[ \t]*)([^·\n]*?)([ \t]*(?:·|$))", re.M)
PHASE_ID = re.compile(r"^P\d+[A-Za-z]?$")
NOT_STARTED_PHASE = ("NOT_STARTED", "PLANNED")
NEXT_H2 = re.compile(r"^##[ \t]+\S", re.M)


class ReconcileError(ValueError):
    pass


def _terms(text):
    return set(tokenize(text or "")) - GENERIC


def locate_phase(index, request, paths=()):
    """(best phase or None, ranking). Phase name counts most, then objective, then task titles; paths match globs."""
    q = _terms(request)
    ranking = []
    for order, p in enumerate((index or {}).get("phases", [])):
        score = (3 * len(q & _terms(p["phase_name"])) + 2 * len(q & _terms(p.get("objective")))
                 + len(q & _terms(" ".join(t["title"] for t in p["tasks"]))))
        score += 2 * sum(1 for path in paths for g in p["affected_paths"] if _glob_match(path, g))
        ranking.append({"phase_id": p["phase_id"], "phase_name": p["phase_name"], "score": score, "order": order})
    ranking.sort(key=lambda r: (-r["score"], r["order"]))
    best = ranking[0] if ranking and ranking[0]["score"] > 0 else None
    return (plan_index.phase(index, best["phase_id"]) if best else None), ranking


def _read_plan(project, state):
    return checked(project, plan_index.plan_file(project, state)).read_text(encoding="utf-8")


def _write_plan(project, state, text):
    atomic.write_text(checked(project, plan_index.plan_file(project, state), "write"), text)


def _append_history(text, line):
    row = f"| {date.today().isoformat()} | {line} |"
    idx = text.find(HISTORY_HEADING)
    if idx < 0:
        return text.rstrip("\n") + f"\n\n{HISTORY_HEADING}\n\n| Date | Change |\n|---|---|\n{row}\n"
    nxt = NEXT_H2.search(text, idx + len(HISTORY_HEADING))
    end = nxt.start() if nxt else len(text)
    section = text[idx:end].rstrip("\n")
    if "|" not in section:
        section += "\n\n| Date | Change |\n|---|---|"
    return text[:idx] + section + f"\n{row}\n" + ("\n" + text[end:] if nxt else "")


def _cell(value):
    return str(value or "—").replace("|", "\\|").replace("\n", " ").strip() or "—"


def _next_task_id(phase):
    num = re.sub(r"\D", "", phase["phase_id"]) or "0"
    used = [int(m.group(1)) for t in phase["tasks"] if (m := re.match(rf"T-{num}\.(\d+)$", t["id"]))]
    return f"T-{num}.{max(used, default=0) + 1}"


def add_task(project, state, index, phase_id, title, **kw):
    """Append a PLANNED task row to the phase's table; reopen a finished phase. Returns (task, reopened).
    Runs under the project's plan lock and re-reads the index inside it, so concurrent sessions never reuse a task id
    or lose a row (`index` is accepted for API symmetry; the locked re-read wins)."""
    from ..events.log import emit
    with project_lock(project, "plan"):
        task, reopened = _add_task_locked(project, state, phase_id, title, **kw)
    emit(project, "STATE_UPDATED", capabilities=kw.get("capabilities") or [],
         details={"change": "task_added", "task": task["id"], "phase": task["phase_id"], "reopened": reopened})
    if reopened:
        emit(project, "PHASE_CHANGED", details={"phase": task["phase_id"], "status": "IN_PROGRESS", "reason": "reopened"})
    return task, reopened


def _add_task_locked(project, state, phase_id, title, *, capabilities=(), impact=None, depends=None, acceptance=None):
    index = plan_index.load_index(project, state)
    p = plan_index.phase(index, phase_id)
    text = _read_plan(project, state)
    start, end = p["section"]["start"], p["section"]["end"]
    section = text[start:end]
    body, trailing = section.rstrip("\n"), section[len(section.rstrip("\n")):] or "\n"
    tid = _next_task_id(p)
    imp = impact or {}
    row = "| " + " | ".join(_cell(v) for v in (
        tid, title, "PLANNED", depends,
        ", ".join(list(capabilities)[:4]),
        (imp.get("security_impact") or {}).get("reason"),
        (imp.get("design_impact") or {}).get("reason"),
        (imp.get("testing_impact") or {}).get("reason"),
        acceptance)) + " |"
    lines = body.split("\n")
    table_rows = [i for i, line in enumerate(lines) if line.lstrip().startswith("|")]
    if table_rows:
        lines.insert(table_rows[-1] + 1, row)
    else:
        lines += ["", "| " + " | ".join(plan_index.TASK_COLUMNS) + " |",
                  "|" + "---|" * len(plan_index.TASK_COLUMNS), row]
    new_section = "\n".join(lines) + trailing
    reopened = p["status"] in DONE_STATES
    if reopened:
        new_section = STATUS_META.sub(r"\g<1>IN_PROGRESS", new_section, count=1)
    text = text[:start] + new_section + text[end:]
    text = _append_history(text, f"{tid} added to {p['phase_id']} {p['phase_name']}: {_cell(title)}"
                                 + (" (phase reopened)" if reopened else ""))
    _write_plan(project, state, text)
    plan_index.load_index(project, state)
    return {"id": tid, "title": title, "status": "PLANNED", "phase_id": p["phase_id"]}, reopened


def set_status(project, state, index, item_id, status, evidence=None):
    """Change a task's (T-…) or phase's (P…) status following the §25 transitions; done states need evidence.
    A task change rolls up into its phase (first task started → phase IN_PROGRESS; every task done → phase VERIFIED
    or COMPLETED with the evidence; a done task reopened → phase IN_PROGRESS), so plan, index and state agree."""
    from ..events.log import emit
    with project_lock(project, "plan"):
        old, rollup = _set_status_locked(project, state, item_id, status, evidence)
    if status in DONE_STATES:
        record_verification(project, item_id, status, evidence)
    details = {"item": item_id, "from": old, "to": status, "evidence": evidence}
    if PHASE_ID.match(item_id):
        emit(project, "PHASE_CHANGED", details=details)
    elif status in STATUS_EVENTS:
        emit(project, STATUS_EVENTS[status], details=details)
    emit(project, "STATE_UPDATED", details={"change": "status", **details})
    if rollup:
        emit(project, "PHASE_CHANGED", details={**rollup, "reason": f"roll-up from {item_id}"})
    if rollup or PHASE_ID.match(item_id):
        index = plan_index.load_index(project, state, rebuild=True)
        update_state(project, lambda s: s["plan"].__setitem__("current_phase", index.get("current_phase")))
    return old


def _phase_rollup(phase, evidence):
    """The phase status its tasks imply now, or None when the phase stays as it is."""
    tasks = [t for t in phase["tasks"] if t["status"] != "INTENTIONALLY_DEFERRED"]
    if not tasks:
        return None
    if all(t["status"] in DONE_STATES for t in tasks):
        target = "COMPLETED" if all(t["status"] == "COMPLETED" for t in tasks) else "VERIFIED"
        return target if phase["status"] not in DONE_STATES and evidence else None
    if phase["status"] in DONE_STATES + NOT_STARTED_PHASE and any(t["status"] not in NOT_STARTED_PHASE for t in tasks):
        return "IN_PROGRESS"
    return None


def _set_phase_meta(section, status, evidence=None):
    section = STATUS_META.sub(rf"\g<1>{status}", section, count=1)
    if evidence:
        section = EVIDENCE_META.sub(lambda m: m.group(1) + _cell(evidence) + m.group(3), section, count=1)
    return section


def _set_status_locked(project, state, item_id, status, evidence):
    index = plan_index.load_index(project, state)
    text = _read_plan(project, state)
    rollup = None
    if PHASE_ID.match(item_id):
        p = plan_index.phase(index, item_id)
        old = p["status"]
        check_transition(old, status, evidence)
        start, end = p["section"]["start"], p["section"]["end"]
        section = text[start:end]
        if STATUS_META.search(section):
            section = _set_phase_meta(section, status, evidence if status in DONE_STATES else None)
        else:
            section = section.replace("\n", f"\nStatus: {status}\n", 1)
        text = text[:start] + section + text[end:]
    else:
        old = next((t["status"] for p in index["phases"] for t in p["tasks"] if t["id"] == item_id), None)
        if old is None:
            raise ReconcileError(f"no task {item_id} in the plan")
        check_transition(old, status, evidence)
        pattern = re.compile(rf"^(\|[ \t]*{re.escape(item_id)}[ \t]*\|[^|\n]*\|[ \t]*)([A-Z_]+)", re.M)
        text, n = pattern.subn(rf"\g<1>{status}", text, count=1)
        if not n:
            raise ReconcileError(f"could not find the status cell of {item_id}")
        # Roll the change up into the task's phase (derived status: the §25 phase transition table is not consulted).
        phase = next(p for p in plan_index.parse_plan(text) if any(t["id"] == item_id for t in p["tasks"]))
        target = _phase_rollup(phase, evidence)
        if target:
            start, end = phase["section"]["start"], phase["section"]["end"]
            text = text[:start] + _set_phase_meta(text[start:end], target,
                                                  evidence if target in DONE_STATES else None) + text[end:]
            rollup = {"item": phase["phase_id"], "from": phase["status"], "to": target,
                      "evidence": evidence if target in DONE_STATES else None}
    text = _append_history(text, f"{item_id}: {old} → {status}" + (f" (evidence: {_cell(evidence)})" if evidence else ""))
    if rollup:
        text = _append_history(text, f"{rollup['item']}: {rollup['from']} → {rollup['to']} (roll-up from {item_id})")
    _write_plan(project, state, text)
    plan_index.load_index(project, state)
    return old, rollup


def reconcile(project, state, router, request, paths=(), new_phase=None):
    """Spec §56 for one change request. Returns a report; `needs_phase` when no phase matches and none was named."""
    from ..routing import ProjectFacts
    index = plan_index.load_index(project, state)
    if index is None:
        raise ReconcileError("no implementation plan (create docs/IMPLEMENTATION_PLAN.md or run "
                             "`agylite project init --docs`)")
    route = router.route(request, paths=paths, project=ProjectFacts(
        stage=state["project"]["stage"], project_id=project.project_id, phase=index.get("current_phase"),
        stack=tuple(state.get("stack") or ())))
    phase, ranking = locate_phase(index, request, paths)
    if phase is None and new_phase:
        pid = _add_phase(project, state, index, new_phase)
        index = plan_index.load_index(project, state, rebuild=True)
        phase = plan_index.phase(index, pid)
    if phase is None:
        return {"status": "needs_phase", "route": route, "ranking": ranking[:5],
                "message": "no existing phase matches; pass --new-phase \"<name>\" to add one to the same plan"}
    imp = change_impact(route, phase, paths)
    task, reopened = add_task(project, state, index, phase["phase_id"], request.strip().rstrip("."),
                              capabilities=[c["id"] for c in route["capabilities"]], impact=imp)
    index = plan_index.load_index(project, state, rebuild=True)
    update_state(project, lambda s: s["plan"].__setitem__("current_phase", index.get("current_phase")))
    return {"status": "planned", "phase": {"phase_id": phase["phase_id"], "phase_name": phase["phase_name"]},
            "task": task, "reopened": reopened, "impact": imp,
            "route_capabilities": [c["id"] for c in route["capabilities"]],
            "decision_needed": "engineering/architecture" in imp["affected_subdomain"],
            "files_changed": [index["plan_path"], ".agylite/plan-index.yaml", ".agylite/state.yaml"]}


def _add_phase(project, state, index, name):
    with project_lock(project, "plan"):
        return _add_phase_locked(project, state, name)


def _add_phase_locked(project, state, name):
    index = plan_index.load_index(project, state)
    nums = [int(re.sub(r"\D", "", p["phase_id"]) or 0) for p in index["phases"]]
    pid = f"P{max(nums, default=0) + 1}"
    text = _read_plan(project, state)
    block = (f"## {pid} · {name}\nStatus: PLANNED · Depends: — · Paths: — · Flags: — · Evidence: —\nObjective: {name}\n\n"
             "| " + " | ".join(plan_index.TASK_COLUMNS) + " |\n|" + "---|" * len(plan_index.TASK_COLUMNS) + "\n\n")
    idx = text.find(HISTORY_HEADING)
    text = (text[:idx] + block + text[idx:]) if idx >= 0 else text.rstrip("\n") + "\n\n" + block
    text = _append_history(text, f"{pid} {name} added")
    _write_plan(project, state, text)
    plan_index.load_index(project, state)
    return pid


def register(project):
    """Machine-local project record (identity → root) used by relink and the dashboard."""
    path = checked(project, project.data_dir / "project.yaml", "write")
    rec = read_yaml(path) or {"project_id": project.project_id, "root": str(project.root), "origin": project.origin,
                              "name": project.name, "created": date.today().isoformat(), "aliases": []}
    rec["root"] = str(project.root)
    write_yaml(path, rec)
    return rec
