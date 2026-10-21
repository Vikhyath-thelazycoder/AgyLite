"""eng-addy: Addy's behavioural evals in three arms (baseline · Addy's skill via --append-system-prompt · Agylite)."""
import json

from .. import harness
from . import addy_style, upstreams_dir

METRICS = addy_style.METRICS


def _case(skill):
    return json.loads((upstreams_dir() / "agent-skills" / "evals" / "cases" / f"{skill}.json").read_text(encoding="utf-8"))


def cells(cfg):
    return [{"task": f"{t['skill']}#{t['eval']}", "skill": t["skill"], "eval": t["eval"]} for t in cfg["tasks"]]


def run_cell(cell, ctx):
    ev = next(e for e in _case(cell["skill"])["evals"] if e["id"] == cell["eval"])
    skill_text = None
    if ctx["arm"] == "baseline":
        arm = harness.ArmSetup("baseline")
    elif ctx["arm"] == "upstream":
        arm = harness.ArmSetup("upstream")
        skill_text = (upstreams_dir() / "agent-skills" / "skills" / cell["skill"] / "SKILL.md").read_text(encoding="utf-8")
    else:
        arm = harness.agylite_arm(ctx["run_dir"], ctx.get("python"))
    return addy_style.run_eval(ev, arm, fixtures=upstreams_dir() / "agent-skills" / "evals" / "fixtures",
                               model=ctx["model"], out_dir=ctx["run_dir"] / "traces", label=ctx["label"],
                               skill_text=skill_text, grader_model=ctx.get("judge_model"))
