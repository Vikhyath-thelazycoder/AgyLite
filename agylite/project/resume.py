"""Handoff across sessions and the project's next step (gap programme G1: A `agylite next`, C `agylite handoff`).

A handoff is three short texts the agent writes when work pauses (done / left / next); the next session start shows it.
`next_step` reads only the compact state and plan index (no plan read): an unanswered blocking question, then the
handoff, then active tasks, then the first planned task.
"""
from __future__ import annotations

from .state import checked, now, read_yaml, write_yaml

HANDOFF_FILE = "handoff.yaml"
FIELDS = ("done", "left", "next")
MAX_CHARS = 600   # per field: a handoff is a pointer into the plan, not a second plan (it is shown at session start)


def handoff_path(project):
    return project.state_dir / HANDOFF_FILE


def read_handoff(project):
    return read_yaml(checked(project, handoff_path(project)))


def write_handoff(project, *, done: str, left: str, next: str, session_id=None):
    data = {"written": now(), "session": session_id,
            **{k: " ".join((v or "").split())[:MAX_CHARS] for k, v in (("done", done), ("left", left), ("next", next))}}
    if not data["next"]:
        raise ValueError("a handoff needs --next: the first thing the next session does")
    path = checked(project, handoff_path(project), "write")
    path.parent.mkdir(parents=True, exist_ok=True)
    write_yaml(path, data)
    return data


def clear_handoff(project) -> bool:
    path = checked(project, handoff_path(project), "write")
    if not path.is_file():
        return False
    path.unlink()
    return True


def handoff_lines(handoff) -> list:
    """Lines for the session start and `agylite next` (empty fields are left out)."""
    if not handoff:
        return []
    return ([f"handoff from {handoff.get('written', '?')} (`agylite handoff clear` when it is done):"]
            + [f"  {k}: {handoff[k]}" for k in FIELDS if handoff.get(k)])


def _tasks(index, statuses):
    return [(p, t) for p in (index or {}).get("phases", []) for t in p["tasks"] if t["status"] in statuses]


def next_step(state, index, handoff=None) -> dict:
    """{step, why, command}: the one thing to do next in this project."""
    if state is None:
        return {"step": "Initialise the project", "why": "there is no project state yet",
                "command": "agylite project init"}
    open_q = [q for q in state.get("pending_questions") or [] if q not in (state.get("answers") or {})]
    if open_q:
        return {"step": f"Answer the blocking requirements question {open_q[0]}",
                "why": f"{len(open_q)} blocking question(s) are open and no task can start before they are answered",
                "command": f'agylite project answer {open_q[0]} "<answer>"'}
    if handoff and handoff.get("next"):
        return {"step": handoff["next"], "why": f"the last session paused here ({handoff.get('written', '?')})",
                "command": "agylite handoff show"}
    if index is None:
        return {"step": "Write the plan", "why": "the project has no implementation plan",
                "command": "agylite project init --docs"}
    for statuses, verb, why, command in (
            (("READY_FOR_VERIFICATION",), "Verify", "it is implemented and waits for verification", "agylite verify"),
            (("IN_PROGRESS", "PARTIALLY_COMPLETE"), "Finish", "it is started and not finished", "agylite plan show {phase}"),
            (("BLOCKED",), "Unblock", "it is blocked", "agylite plan show {phase}"),
            (("PLANNED", "NOT_STARTED"), "Start", "it is the first task not started", "agylite plan set-status {task} IN_PROGRESS")):
        found = _tasks(index, statuses)
        if found:
            phase, task = found[0]
            return {"step": f"{verb} {task['id']} {task['title']} (phase {phase['phase_id']} {phase['phase_name']})",
                    "why": why, "command": command.format(phase=phase["phase_id"], task=task["id"])}
    cur = next((p for p in index["phases"] if p["phase_id"] == index.get("current_phase")), None)
    if cur:
        return {"step": f"Add tasks to phase {cur['phase_id']} {cur['phase_name']}",
                "why": f"the phase is {cur['status']} and has no open task",
                "command": f'agylite plan add-task {cur["phase_id"]} "<title>" --acceptance "<criteria>"'}
    return {"step": "Nothing is open", "why": "every phase and task in the plan is finished",
            "command": 'agylite plan reconcile "<the next request>"'}
