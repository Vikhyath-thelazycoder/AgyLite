"""Addy-shaped cases (fixture workspace, prompt, numbered expectations, Addy's grader) whose original arm is the
upstream as it ships: exported whole from its pinned commit and given to Claude Code either as a project skill (a skill
folder, e.g. Cloudflare security-audit with its domain files) or as a plugin (`--plugin-dir`, e.g. EGM with its agents,
standards and `${CLAUDE_PLUGIN_ROOT}`). Used by the Step 5 suites `security` and `spec-review`.

suite.yaml: `upstream: {export: "<repo>:<path>", mode: project_skill|plugin, plugin: <name>, prompt_prefix: "…"}`;
`prompt_prefix` is how the original is invoked when its skills cannot be model-invoked (EGM: `/egm:egm-review `)."""
import io
import json
import shutil
import subprocess
import tarfile
from pathlib import Path

from .. import harness
from . import HERE, addy_style, load_suite

METRICS = addy_style.METRICS


def cells(cfg):
    return [{"task": f"{t['case']}#{t.get('eval', 1)}", "suite": cfg["name"], **t} for t in cfg["tasks"]]


def export(spec: str, dest: Path) -> Path:
    """`<repo>:<path>` (`.` = the whole repo) from its pinned commit via `git archive`, once per run."""
    from ....bundle.build import default_staging
    from ....bundle.rules import evidence_dir, load_yaml
    from ....paths import agylite_home
    repo, path = spec.split(":", 1)
    target = dest / (repo if path == "." else Path(path).name)
    if target.is_dir():
        return target
    pin = load_yaml(evidence_dir() / "upstream-staging-snapshot.yaml")["snapshots"][repo]["head"]
    tar = subprocess.run(["git", "-C", str(default_staging(agylite_home()) / repo), "archive", pin,
                          *([] if path == "." else [path])], capture_output=True, check=True).stdout
    tmp = dest / f".export-{repo}"
    shutil.rmtree(tmp, ignore_errors=True)
    with tarfile.open(fileobj=io.BytesIO(tar)) as t:
        t.extractall(tmp, filter="data")
    shutil.move(str(tmp if path == "." else tmp / path), target)
    shutil.rmtree(tmp, ignore_errors=True)
    return target


def upstream_arm(up: dict, run_dir: Path) -> harness.ArmSetup:
    src = export(up["export"], run_dir / "upstream-skills")
    if up.get("mode") == "plugin":
        return harness.ArmSetup("upstream", args=["--plugin-dir", str(src)], plugins=(up["plugin"],))
    return harness.ArmSetup("upstream", project_skills=(str(src),))


def run_cell(cell, ctx):
    cfg = load_suite(cell["suite"])
    here = HERE / cell["suite"]
    case = json.loads((here / f"cases-{cell['case']}.json").read_text(encoding="utf-8"))
    ev = dict(next(e for e in case["evals"] if e["id"] == cell.get("eval", 1)))
    if ctx["arm"] == "baseline":
        arm = harness.ArmSetup("baseline")
    elif ctx["arm"] == "upstream":
        arm = upstream_arm(cfg["upstream"], ctx["run_dir"])
        ev["prompt"] = cfg["upstream"].get("prompt_prefix", "") + ev["prompt"]
    else:
        arm = harness.agylite_arm(ctx["run_dir"], ctx.get("python"))
    return addy_style.run_eval(ev, arm, fixtures=here / "fixtures", model=ctx["model"], out_dir=ctx["run_dir"] / "traces",
                               label=ctx["label"], grader_model=ctx.get("judge_model"), timeout=cfg.get("timeout_s", 900))
