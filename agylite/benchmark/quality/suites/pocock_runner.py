"""eng-pocock: Agylite-written cases for Pocock's skills in Addy's shape, three arms, Addy's grader."""
import json
from pathlib import Path

from .. import harness
from . import addy_style, upstreams_dir

METRICS = addy_style.METRICS
HERE = Path(__file__).resolve().parent / "eng-pocock"


def cells(cfg):
    return [{"task": f"{t['skill']}#{t['eval']}", **t} for t in cfg["tasks"]]


def run_cell(cell, ctx):
    case = json.loads((HERE / f"cases-{cell['skill']}.json").read_text(encoding="utf-8"))
    ev = next(e for e in case["evals"] if e["id"] == cell["eval"])
    skill_text = None
    if ctx["arm"] == "baseline":
        arm = harness.ArmSetup("baseline")
    elif ctx["arm"] == "upstream":
        arm = harness.ArmSetup("upstream")
        skill_text = (upstreams_dir() / "skills" / "skills" / cell["path"] / "SKILL.md").read_text(encoding="utf-8")
    else:
        arm = harness.agylite_arm(ctx["run_dir"], ctx.get("python"))
    return addy_style.run_eval(ev, arm, fixtures=HERE / "fixtures", model=ctx["model"],
                               out_dir=ctx["run_dir"] / "traces", label=ctx["label"], skill_text=skill_text,
                               grader_model=ctx.get("judge_model"))
