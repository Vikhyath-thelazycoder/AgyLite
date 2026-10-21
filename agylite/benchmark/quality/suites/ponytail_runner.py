"""eng-ponytail: Ponytail's own agentic runner (imported unchanged) in three arms — baseline · ponytail (its plugin
from the clone) · agylite (its `ponytail2` plugin arm pointed at this checkout, allowed to run `agylite` only)."""
import os
import sys
from contextlib import contextmanager

from .. import harness
from . import upstreams_dir

METRICS = {"correct": False, "safe": False, "src_loc": True, "wrote_tests": False, "cost": True}
AGYLITE_TOOLS = "Read,Write,Edit,Glob,Grep,Bash(agylite:*),Bash(*/bin/agylite:*)"


def _run_module():
    path = str(upstreams_dir() / "ponytail" / "benchmarks" / "agentic")
    if path not in sys.path:
        sys.path.insert(0, path)
    import run   # noqa: PLC0415 — Ponytail's runner, imported as-is
    return run


@contextmanager
def _env(values):
    old = {k: os.environ.get(k) for k in values}
    os.environ.update(values)
    try:
        yield
    finally:
        for k, v in old.items():
            os.environ.pop(k, None) if v is None else os.environ.__setitem__(k, v)


def cells(cfg):
    return [{"task": t} for t in cfg["tasks"]]


def run_cell(cell, ctx):
    run = _run_module()
    base = run._base_cmd
    ws = harness.fresh_workspace(ctx["label"])
    env = {"PONYTAIL_PLUGIN_DIR": str(upstreams_dir() / "ponytail")}
    pt_arm = {"baseline": "baseline", "upstream": "ponytail", "agylite": "ponytail2"}[ctx["arm"]]
    model = ctx["model"]

    def cmd(claude, prompt, _model):
        c = base(claude, prompt, model)
        if ctx["arm"] == "agylite":   # the pilot's one fairness adjustment: Bash for `agylite` only
            i = c.index("--disallowedTools")
            del c[i:i + 2]
            c[c.index("bypassPermissions")] = "acceptEdits"
            c += ["--allowedTools", AGYLITE_TOOLS]
        return c
    if ctx["arm"] == "agylite":
        arm = harness.agylite_arm(ctx["run_dir"], ctx.get("python"))
        env.update(arm.env, PONYTAIL2_PLUGIN_DIR=arm.args[1])
    run._base_cmd = cmd
    try:
        with _env(env):
            res = run.run_cell(cell["task"], pt_arm, model, ws)
    finally:
        run._base_cmd = base
    metrics = {"correct": res.get("correct"), "safe": res.get("safe"), "src_loc": res.get("src_loc"),
               "wrote_tests": 1 if (res.get("test_loc") or 0) > 0 else 0, "cost": res.get("cost")}
    return {"label": ctx["label"], "arm": ctx["arm"], "workspace": str(ws), "metrics": metrics,
            "cost": res.get("cost"), "duration_ms": res.get("duration_ms"), "turns": res.get("turns"),
            "scorer": {k: res.get(k) for k in ("reason", "src_files", "total_loc", "test_loc", "denials")}}
