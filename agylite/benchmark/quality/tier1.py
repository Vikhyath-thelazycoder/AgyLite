"""MP2 Tier 1: run a suite's cells in three arms, score with the upstream's own instrument, compute retained gain.

Spend control: `dry_run` prints the session matrix; without `yes_spend` no paid session starts; `max_sessions` caps
the run. Runs alternate arm order per run index; one session at a time. Traces stay under ~/.agylite/benchmarks/.
A usage-limit or rate-limit reply stops the run (report `stopped`, `resume`); `resume=<run dir>` keeps that run's
valid records and runs only the cells still missing.
"""
import json
from datetime import datetime, timezone
from pathlib import Path

from ...paths import agylite_home, current_bundle
from . import harness, scoring, suites

ARMS = ("baseline", "upstream", "agylite")


def plan(suite: str, arms=ARMS, runs=1, tasks=None):
    cfg = suites.load_suite(suite)
    mod = suites.module(cfg)
    cells = [c for c in mod.cells(cfg) if not tasks or c["task"] in tasks]
    matrix = []
    for r in range(runs):
        order = list(arms) if r % 2 == 0 else list(reversed(arms))   # alternate arm order between runs
        for c in cells:
            for arm in order:
                matrix.append({**c, "arm": arm, "run": r})
    return cfg, mod, matrix


def _valid(rec) -> bool:
    """A finished cell: no error, no isolation problem, not a limit reply recorded as an answer, and at least one
    measured metric (an invalid grader reply scores nothing)."""
    if rec.get("error") or rec.get("isolation_error") or harness.is_usage_limit(rec.get("result")):
        return False
    return any(v is not None for v in (rec.get("metrics") or {}).values())


def run(suite: str, *, arms=ARMS, runs=1, tasks=None, dry_run=False, yes_spend=False, max_sessions=None,
        model=None, judge_model=None, python=None, out_root: Path | None = None, log=print, ledger=True,
        resume: Path | None = None) -> dict:
    cfg, mod, matrix = plan(suite, arms, runs, tasks)
    if dry_run:
        for m in matrix:
            log(f"[dry-run] {suite} · {m['task']} · {m['arm']} · run {m['run']}")
        log(f"{len(matrix)} sessions planned (none started)")
        return {"suite": suite, "planned": len(matrix), "started": 0}
    if resume:
        run_dir = Path(resume)
        stamp = run_dir.name.split("-", 1)[0]
        kept = {r["label"]: r for r in json.loads((run_dir / "records.json").read_text(encoding="utf-8")) if _valid(r)}
    else:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        run_dir = (out_root or agylite_home() / "benchmarks" / "quality") / f"{stamp}-{suite}"
        kept = {}
    todo = [m for m in matrix if _label(m) not in kept]
    harness.require_spend(yes_spend, len(todo), max_sessions)
    run_dir.mkdir(parents=True, exist_ok=True)
    records, stopped = [kept[_label(m)] for m in matrix if _label(m) in kept], None
    for i, m in enumerate(todo):
        label = _label(m)
        ctx = {"arm": m["arm"], "run_dir": run_dir, "model": model or harness.DEFAULT_MODEL, "judge_model": judge_model,
               "python": python, "label": label, "run": m["run"]}
        log(f"[{i + 1}/{len(todo)}] {suite} · {m['task']} · {m['arm']} …")
        try:
            rec = mod.run_cell(m, ctx)
        except harness.UsageLimit as exc:
            stopped = f"{exc} (at {label}, {len(records)}/{len(matrix)} cells done)"
            log(f"    stopped: {stopped}")
            break
        except Exception as exc:   # one broken cell is recorded, never silently dropped
            rec = {"label": label, "arm": m["arm"], "error": f"{type(exc).__name__}: {exc}"[:400], "metrics": {}}
        rec.pop("_trace", None)
        rec.update(task=m["task"], run=m["run"])
        if m["arm"] == "agylite" and rec.get("workspace"):
            rec["agylite_usage"] = harness.agylite_usage(run_dir / "agylite-home", Path(rec["workspace"]))
        log(f"    metrics {rec.get('metrics')} cost {rec.get('cost')} {rec.get('isolation_error') or rec.get('error') or ''}")
        records.append(rec)
        (run_dir / "records.json").write_text(json.dumps(records, indent=1, default=str), encoding="utf-8")
    if not stopped and hasattr(mod, "finalize"):   # suite-level steps that need every arm (e.g. a blind judge)
        try:
            records = mod.finalize(records, {"run_dir": run_dir, "judge_model": judge_model})
        except harness.UsageLimit as exc:
            stopped = f"{exc} (in the suite's final judging step; every cell is done)"
        (run_dir / "records.json").write_text(json.dumps(records, indent=1, default=str), encoding="utf-8")
    if stopped:   # no verdict and no ledger row from a partial run
        resume_cmd = f"agylite benchmark --quality --tier 1 --suite {suite} --yes-spend --resume {run_dir}"
        report = {"suite": suite, "run_dir": str(run_dir), "date": stamp, "sessions": len(records),
                  "planned": len(matrix), "stopped": stopped, "resume": resume_cmd, "verdict": "stopped"}
        (run_dir / "report.json").write_text(json.dumps(report, indent=1, default=str), encoding="utf-8")
        if ledger:
            from . import ledger as parity_ledger
            parity_ledger.note(f"{stamp} {suite}: stopped by a usage limit after {len(records)}/{len(matrix)} "
                               f"cells; resume: `{resume_cmd}`")
        return report
    report = score(suite, cfg, mod, records)
    report.update(run_dir=str(run_dir), model=model or harness.DEFAULT_MODEL, judge_model=judge_model,
                  bundle=(current_bundle().name if current_bundle() else None), date=stamp, runs=runs,
                  isolation="real (--setting-sources project,local --strict-mcp-config; init event checked)")
    (run_dir / "report.json").write_text(json.dumps(report, indent=1, default=str), encoding="utf-8")
    if ledger:
        from . import ledger as parity_ledger
        parity_ledger.append(report)   # IMPLEMENTATION_PLAN §6: every run is recorded
    return report


def _label(m) -> str:
    return f"{m['task'].replace('/', '_').replace('#', '-')}__{m['arm']}__{m['run']}"


def score(suite, cfg, mod, records) -> dict:
    """Per task and per metric: values per arm, retained gain and verdict; suite verdict = weakest metric."""
    tasks = sorted({r["task"] for r in records})
    per_task, pooled = {}, {m: {a: [] for a in ARMS} for m in mod.METRICS}
    for t in tasks:
        per_task[t] = {}
        for metric, lower in mod.METRICS.items():
            vals = {a: [r["metrics"].get(metric) for r in records if r["task"] == t and r["arm"] == a
                        and r.get("metrics", {}).get(metric) is not None] for a in ARMS}
            for a in ARMS:
                pooled[metric][a] += vals[a]
            per_task[t][metric] = scoring.verdict(vals["baseline"], vals["upstream"], vals["agylite"], lower)
    overall = {m: scoring.verdict(v["baseline"], v["upstream"], v["agylite"], mod.METRICS[m]) for m, v in pooled.items()}
    cost = {a: round(sum(r.get("cost") or 0 for r in records if r["arm"] == a), 4) for a in ARMS}
    secs = {a: round(sum((r.get("duration_ms") or 0) for r in records if r["arm"] == a) / 1000, 1) for a in ARMS}
    return {"suite": suite, "target": cfg.get("target"), "metrics": overall, "per_task": per_task,
            "verdict": scoring.suite_verdict(overall), "cost_usd": cost, "agent_seconds": secs,
            "sessions": len(records), "errors": [r["label"] for r in records if r.get("error") or r.get("isolation_error")],
            "agylite_usage": [r.get("agylite_usage") for r in records if r["arm"] == "agylite"]}


def render(rep: dict) -> str:
    if rep.get("stopped"):
        return (f"## {rep['suite']}: STOPPED ({rep['sessions']}/{rep['planned']} cells done)\n\n{rep['stopped']}\n"
                f"RESUME FROM: {rep['resume']}\n")
    lines = [f"## {rep['suite']}: {rep['verdict'].upper()} (n={rep.get('runs')}, model {rep.get('model')})", "",
             "| metric | no skill | original | AgyLite | retained | verdict |", "|---|---:|---:|---:|---:|---|"]
    fmt = lambda v: "—" if v is None else f"{v:.3g}"   # noqa: E731
    for m, v in rep["metrics"].items():
        lines.append(f"| {m}{' (lower is better)' if v.get('lower_is_better') else ''} | {fmt(v['baseline'])} | "
                     f"{fmt(v['upstream'])} | {fmt(v['agylite'])} | {fmt(v.get('retained'))} | {v['verdict']}"
                     f"{' (' + v['note'] + ')' if v.get('note') else ''} |")
    lines += ["", f"Cost (USD) per arm: {rep['cost_usd']} · agent time (s): {rep['agent_seconds']}"]
    if rep["errors"]:
        lines.append(f"Errors/isolation problems: {', '.join(rep['errors'])}")
    return "\n".join(lines) + "\n"
