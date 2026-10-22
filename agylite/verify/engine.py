"""`agylite verify` (P15, D-035): detect → impact (P12) → select → run → rerun failed once → evidence → state.

Local test-first only. Failed tests are rerun once to separate flaky from failing; the evidence file records both.
"""
from datetime import datetime, timezone

from ..events import emit
from . import detect, evidence, run, select

RERUN_KINDS = ("test",)


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def plan_for(project, paths=None, *, full=False, kinds=None, include_e2e=False, bundle_dir=None, inspect=None,
             diagrams=None):
    from ..codebase import affected
    from . import design, diagram
    checks = detect.detect(project.root)
    impact = None if full else affected(project, paths, bundle_dir=bundle_dir)
    selected = select.plan(checks, impact, full=full, kinds=kinds, include_e2e=include_e2e)
    if not kinds or "design" in kinds:   # MP4 §3.3: style/markup changes also need design check + Taste lint/inspect
        changed = (impact or {}).get("changed") or list(paths or [])
        selected += design.checks(project, changed, inspect=inspect, bundle_dir=bundle_dir)
    if not kinds or "diagram" in kinds:   # MP5 §3.3: delivered diagrams pass Archify check + Chrome browser-check
        changed = (impact or {}).get("changed") or list(paths or [])
        selected += diagram.checks(project, changed, named=diagrams)
    return impact, selected


def describe(selected, impact):
    return {
        "impact": ({"method": impact["method"], "changed": impact["changed"], "notice": impact["notice"]}
                   if impact else None),
        "checks": [{"kind": c.kind, "name": c.name, "command": cmd, "reason": why,
                    "tests": [{"file": t, "kind": select.test_kind(t)} for t in tests], "notes": c.notes}
                   for c, cmd, why, tests in selected],
    }


def active_task(project):
    """The plan task being worked on when exactly one is IN_PROGRESS or READY_FOR_VERIFICATION, else None."""
    from ..project import plan_index, state as pstate
    try:
        st = pstate.load_state(project)
        index = plan_index.load_index(project, st) if st else None
    except Exception:   # noqa: BLE001 — a broken plan never blocks verification; the run is just not tied to a task
        return None
    active = [t["id"] for p in (index or {}).get("phases", []) for t in p["tasks"]
              if t["status"] in ("IN_PROGRESS", "READY_FOR_VERIFICATION")]
    return active[0] if len(active) == 1 else None


def verify(project, paths=None, *, full=False, kinds=None, include_e2e=False, task=None, bundle_dir=None,
           timeout=run.DEFAULT_TIMEOUT, session_id=None, inspect=None, diagrams=None):
    from . import design, diagram
    task = task or active_task(project)
    impact, selected = plan_for(project, paths, full=full, kinds=kinds, include_e2e=include_e2e, bundle_dir=bundle_dir,
                                inspect=inspect, diagrams=diagrams)
    emit(project, "VERIFICATION_STARTED", session_id=session_id, capabilities=["testing/local-verification"],
         details={"checks": len(selected), "task": task})
    results = []
    for c, cmd, why, tests in selected:
        if cmd is None:   # NOT_RUN (e.g. no node>=22 or browser): blocked, never a silent pass
            results.append({"command": [c.name], "exit_code": "NOT_RUN", "result": "BLOCKED", "duration_ms": 0,
                            "diagnosis": list(c.notes), "kind": c.kind, "name": c.name, "reason": why,
                            "tests": tests, "at": _now()})
            continue
        r = run.run_check(cmd, project.root, timeout)
        if c.name == "taste inspect":
            r.update(design.inspect_result(project.root, r))
        if c.kind == "diagram":
            r.update(diagram.result(project.root, why))
        if r["result"] == "FAILED" and c.kind in RERUN_KINDS:
            again = run.run_check(cmd, project.root, timeout)
            r["rerun"] = {"exit_code": again["exit_code"], "result": again["result"]}
            r["flaky"] = again["result"] == "PASSED"   # flaky stays FAILED until fixed
        r.update({"kind": c.kind, "name": c.name, "reason": why, "tests": tests, "at": _now()})
        results.append(r)
    record = {"schema_version": 1, "mode": "local-test-first", "task": task, "result": evidence.overall(results),
              "impact": describe(selected, impact)["impact"],
              "checks": [{k: v for k, v in r.items() if k != "output_tail"} for r in results], "at": _now()}
    rel = evidence.write(project, record)
    from ..project import state as pstate
    if pstate.load_state(project) is not None:
        pstate.record_verification(project, task, record["result"], rel)
    emit(project, "VERIFICATION_PASSED" if record["result"] == "PASSED" else "VERIFICATION_FAILED",
         session_id=session_id, capabilities=["testing/local-verification"],
         details={"result": record["result"], "evidence": rel,
                  "failed": [r["name"] for r in results if r["result"] != "PASSED"]})
    return record, rel, results
