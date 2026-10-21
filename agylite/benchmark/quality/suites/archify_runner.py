"""diagram-archify: Archify's ordinary-model-floor cases in three arms, verified by its own benchmark.mjs."""
import json
import re
import shutil
import subprocess
from pathlib import Path

from .. import harness
from . import upstreams_dir

METRICS = {"first_pass_usable": False, "semantic": False, "validation": False}
TOOLS = "Read,Glob,Grep,Edit,Write,Bash"
REVIEW = """You are reviewing a rendered architecture/flow diagram for visible defects. Read every image listed below
(light and dark themes). Report only defects you can see. Use these tags: clipping, node-overlap, label-overlap,
hidden-route, stacked-edge, weak-hierarchy, unbalanced-whitespace, theme-contrast.

Images: {images}

Return ONLY JSON: {{"status": "passed" | "failed", "defects": ["tag", …], "notes": "…"}}"""


def _root():
    return upstreams_dir() / "archify"


def cells(cfg):
    return [{"task": t} for t in cfg["tasks"]]


def _node(*args, cwd):
    return subprocess.run(["node", *args], cwd=cwd, capture_output=True, text=True, timeout=600)


def run_cell(cell, ctx):
    bench = _root() / "benchmarks" / "ordinary-model-floor"
    case = bench / "cases" / f"{cell['task']}.case.json"
    case_id = json.loads(case.read_text(encoding="utf-8"))["id"]
    dtype = cell["task"].rsplit(".", 1)[1]
    prompt = (bench / "prompts" / f"{cell['task']}.md").read_text(encoding="utf-8")
    ws = harness.fresh_workspace(ctx["label"])
    if ctx["arm"] == "upstream":   # fair-run protocol: generate from the packaged skill root
        shutil.copytree(_root() / "archify", ws, dirs_exist_ok=True)
        arm = harness.ArmSetup("upstream")
    elif ctx["arm"] == "baseline":
        arm = harness.ArmSetup("baseline")
    else:
        arm = harness.agylite_arm(ctx["run_dir"], ctx.get("python"))
    rec = harness.run_session(prompt, ws, arm, model=ctx["model"], allowed_tools=TOOLS, timeout=900,
                              out_dir=ctx["run_dir"] / "traces", label=ctx["label"])
    rec.pop("_trace", None)
    out = ctx["run_dir"] / "archify" / ctx["label"]
    out.mkdir(parents=True, exist_ok=True)
    meta = {"schema_version": 1, "case_id": case_id, "agent": f"claude-code/{ctx['arm']}", "model": ctx["model"],
            "attempt": 1}
    cand = ws / "benchmark-candidate.json"
    if not cand.is_file():
        (out / "run.json").write_text(json.dumps(meta), encoding="utf-8")
        p = _node(str(bench / "benchmark.mjs"), "record-failure", "--case", str(case), "--run", str(out / "run.json"),
                  "--failure", "timeout" if rec.get("killed") else "no_candidate", cwd=_root())
        rec["receipt"] = p.stdout[-2000:]
        rec["metrics"] = {"first_pass_usable": 0, "semantic": 0, "validation": 0}
        return rec
    frozen = out / f"candidate.{dtype}.json"
    shutil.copy2(cand, frozen)   # attempt 1 is frozen before any verification
    cli = str(_root() / "archify" / "bin" / "archify.mjs")
    html = out / "candidate.html"
    _node(cli, "render", dtype, str(frozen), str(html), "--quality", "showcase", cwd=out)
    review = {"status": "skipped", "reviewer": "", "defects": []}
    if html.is_file():
        _node(cli, "visual-check", str(html), "--json", "--out-dir", str(out / "visual"), cwd=out)
        shots = sorted((out / "visual").glob("*.png"))
        if shots:
            raw = subprocess.run(["claude", "-p", "--setting-sources", "project,local", "--strict-mcp-config",
                                  "--model", ctx.get("judge_model") or harness.DEFAULT_MODEL, "--allowedTools", "Read"],
                                 input=REVIEW.format(images=", ".join(str(s) for s in shots)), text=True,
                                 capture_output=True, cwd=out, timeout=600).stdout
            m = re.search(r"\{[\s\S]*\}", raw)
            try:
                got = json.loads(m.group(0)) if m else {}
                review = {"status": got.get("status", "skipped"), "defects": got.get("defects") or [],
                          "reviewer": f"claude-code -p {ctx.get('judge_model') or harness.DEFAULT_MODEL}"}
            except ValueError:
                pass
    (out / "run.json").write_text(json.dumps({**meta, "visual_review": review}), encoding="utf-8")
    p = _node(str(bench / "benchmark.mjs"), "verify", "--case", str(case), "--candidate", str(frozen),
              "--run", str(out / "run.json"), cwd=_root())
    (out / "receipt.json").write_text(p.stdout, encoding="utf-8")
    try:
        receipt = json.loads(p.stdout)
        gates = receipt.get("gates") or {}
        rec["metrics"] = {"first_pass_usable": int(bool(receipt.get("firstPassUsable"))),
                          "semantic": int(bool((gates.get("semantic") or {}).get("ok"))),
                          "validation": int(bool((gates.get("validation") or {}).get("ok")))}
        rec["visual_review"] = review
    except ValueError:
        rec["metrics"] = {"first_pass_usable": None, "semantic": None, "validation": None}
        rec["receipt_error"] = (p.stderr or p.stdout)[-1000:]
    return rec
