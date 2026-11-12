"""eng-ecc: Agylite-written cases for the skills ECC owns, in Addy's shape, three arms, Addy's grader."""
import json
import subprocess
from pathlib import Path

from .. import harness
from . import addy_style

METRICS = addy_style.METRICS
HERE = Path(__file__).resolve().parent / "eng-ecc"


def cells(cfg):
    return [{"task": f"{t['skill']}#{t['eval']}", **t} for t in cfg["tasks"]]


def pinned_skill(name: str) -> str:
    """The ECC skill's SKILL.md at the pinned commit (from the staging clone), whatever a local clone has checked out."""
    from ....bundle.build import default_staging
    from ....bundle.rules import evidence_dir, load_yaml
    from ....paths import agylite_home
    pin = load_yaml(evidence_dir() / "upstream-staging-snapshot.yaml")["snapshots"]["ecc"]["head"]
    return subprocess.run(["git", "-C", str(default_staging(agylite_home()) / "ecc"), "show",
                           f"{pin}:skills/{name}/SKILL.md"], capture_output=True, text=True, check=True).stdout


def run_cell(cell, ctx):
    case = json.loads((HERE / f"cases-{cell['skill']}.json").read_text(encoding="utf-8"))
    ev = next(e for e in case["evals"] if e["id"] == cell["eval"])
    skill_text = None
    if ctx["arm"] == "baseline":
        arm = harness.ArmSetup("baseline")
    elif ctx["arm"] == "upstream":
        arm = harness.ArmSetup("upstream")
        skill_text = pinned_skill(cell["skill"])
    else:
        arm = harness.agylite_arm(ctx["run_dir"], ctx.get("python"))
    return addy_style.run_eval(ev, arm, fixtures=HERE / "fixtures", model=ctx["model"],
                               out_dir=ctx["run_dir"] / "traces", label=ctx["label"], skill_text=skill_text,
                               grader_model=ctx.get("judge_model"))
