"""design: Open Design + UI UX Pro Max (one combined design system in AgyLite) against both originals together, built
and measured with design-taste's pipeline: Taste's evals, inspect.mjs, lint.mjs and the blind critique.md judge."""
import io
import shutil
import subprocess
import tarfile
from pathlib import Path

from . import load_suite, taste_runner

METRICS = taste_runner.METRICS
cells = taste_runner.cells
finalize = taste_runner.finalize


def upstream_skills(cfg, dest: Path) -> list:
    """Each `<staged repo>:<path>` exported whole from its pinned commit (`git archive`, nothing checked out), once per
    run: the local upstream clones may sit on other commits, and the staging checkout is sparse."""
    from ....bundle.build import default_staging
    from ....bundle.rules import evidence_dir, load_yaml
    from ....paths import agylite_home
    pins = load_yaml(evidence_dir() / "upstream-staging-snapshot.yaml")["snapshots"]
    staging = default_staging(agylite_home())
    out = []
    for entry in cfg["upstream_skills"]:
        repo, path = entry.split(":", 1)
        target = dest / Path(path).name
        if not (target / "SKILL.md").is_file():
            tar = subprocess.run(["git", "-C", str(staging / repo), "archive", pins[repo]["head"], path],
                                 capture_output=True, check=True).stdout
            tmp = dest / ".export"
            with tarfile.open(fileobj=io.BytesIO(tar)) as t:
                t.extractall(tmp, filter="data")
            shutil.rmtree(target, ignore_errors=True)
            shutil.move(str(tmp / path), target)
            shutil.rmtree(tmp, ignore_errors=True)
        out.append(target)
    return out


def run_cell(cell, ctx):
    skills = upstream_skills(load_suite("design"), ctx["run_dir"] / "upstream-skills") if ctx["arm"] == "upstream" else None
    return taste_runner.run_cell(cell, ctx, suite="design", upstream_skills=skills)
