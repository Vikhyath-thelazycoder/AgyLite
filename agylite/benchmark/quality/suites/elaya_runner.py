"""design-elaya (Step 5, doc 23 §2): landing pages in three arms — no skill, Elaya's landing-page-design whole (the
original, exported from its pinned commit as a project skill), AgyLite (Taste + Elaya Part A). Each page is measured
with Taste's inspect.mjs and lint.mjs (design-taste's pipeline) and graded on the task's conversion expectations by
Addy's grader prompt over the page's HTML (no blind judge: the conversion structure is what this suite measures)."""
import json
from pathlib import Path

from .. import harness
from . import addy_style, case_runner, load_suite, taste_runner

METRICS = {"conversion_passed": False, "inspector_fail": True, "lint_fail": True}


def cells(cfg):
    return [{"task": t["id"], **t} for t in cfg["tasks"]]


def run_cell(cell, ctx):
    cfg = load_suite("design-elaya")
    ws = harness.fresh_workspace(ctx["label"])
    if ctx["arm"] == "baseline":
        arm = harness.ArmSetup("baseline")
    elif ctx["arm"] == "upstream":
        arm = case_runner.upstream_arm(cfg["upstream"], ctx["run_dir"])
    else:
        arm = harness.agylite_arm(ctx["run_dir"], ctx.get("python"))
    rec = harness.run_session(cell["prompt"], ws, arm, model=ctx["model"], allowed_tools=taste_runner.TOOLS,
                              timeout=cfg.get("timeout_s", 1500), out_dir=ctx["run_dir"] / "traces", label=ctx["label"])
    rec.pop("_trace", None)
    page = taste_runner.find_page(ws)
    rec["metrics"] = dict.fromkeys(METRICS)
    if page is None:
        rec["note"] = "no HTML page produced"
        return rec
    out = ctx["run_dir"] / "pages" / ctx["label"]
    out.mkdir(parents=True, exist_ok=True)
    m = taste_runner.measure(page, out, False, ctx["run_dir"] / "taste-tmp")
    html = page.read_text(encoding="utf-8", errors="replace")[:60000]
    grading = None
    for _ in range(2):
        raw = harness.ask(addy_style.grader_prompt(html, cell["expectations"]).replace(
            "You are grading an agent execution trace", "You are grading a built landing page (its HTML is the trace)"),
            model=ctx.get("judge_model"))
        grading = addy_style.parse_grading(raw, len(cell["expectations"]))
        if grading:
            break
    (out / "conversion.grading.json").write_text(json.dumps(grading or {"raw": raw}, indent=1), encoding="utf-8")
    rec["metrics"] = {"conversion_passed": grading["passed"] / grading["total"] if grading else None,
                      "inspector_fail": m["inspector_fail"], "lint_fail": m["lint_fail"]}
    rec["shots"], rec["inspector_findings"] = m["shots"], m["inspector_findings"]
    return rec
