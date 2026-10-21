"""Fetch the pinned upstream snapshots (D-023: the one explicit, user-initiated network step).

Blobless clone + sparse checkout of only the paths the bundle needs (bundled files, renderer inputs,
license/notice files), so the download is a fraction of the full upstream working trees.
"""
import json
import subprocess
from pathlib import Path

from ..paths import repo_root
from .rules import (BUNDLED, classify, compile_rules, evidence_dir, load_capabilities,
                    load_rules, load_yaml, read_inventory)


def _git(*args, cwd=None, stdin=None):
    return subprocess.run(["git", *args], cwd=cwd, input=stdin, capture_output=True, text=True, check=True).stdout.strip()


def needed_paths(evidence: Path):
    """{repo: [paths]} the build reads: bundled files, gstack renderer inputs, license/notice files."""
    rules_doc = load_rules()
    compile_rules(rules_doc, load_capabilities())
    licenses = json.loads((repo_root() / "third_party" / "licenses.json").read_text(encoding="utf-8"))
    needed = {}
    for repo, rr in rules_doc["repos"].items():
        inventory = {p for p, _, _ in read_inventory(evidence, repo)}
        paths = {p for p in inventory if classify(rr, p)["decision"] in BUNDLED}
        if repo == "gstack":  # generated SKILL.md / sections next to bundled templates are renderer inputs
            paths |= {p[: -len(".tmpl")] for p in paths if p.endswith(".tmpl") and p[: -len(".tmpl")] in inventory}
        paths |= set(licenses.get(repo, {}).get("license_files", []))
        paths |= {p for p in (".claude-plugin/plugin.json",) if p in inventory}   # license metadata (no LICENSE file)
        paths |= {p for p in inventory if p.rsplit("/", 1)[-1] == "SKILL.md"}   # skill catalog input (Plan B search)
        needed[repo] = sorted(paths)
    return needed


def fetch(staging: Path, evidence: Path | None = None, log=print):
    """Clone (blobless, sparse) or update each pinned upstream and check out its exact commit."""
    evidence = evidence or evidence_dir()
    pins = load_yaml(evidence / "upstream-staging-snapshot.yaml")["snapshots"]
    needed = needed_paths(evidence)
    staging.mkdir(parents=True, exist_ok=True)
    for name, meta in sorted(pins.items()):
        target, sha = staging / name, meta["head"]
        if not (target / ".git").is_dir():
            log(f"  cloning {meta['repo']} …")
            _git("clone", "--quiet", "--filter=blob:none", "--no-checkout", "--sparse",
                 f"https://github.com/{meta['repo']}.git", str(target))
        _git("sparse-checkout", "set", "--no-cone", "--stdin", cwd=target,
             stdin="".join(f"/{p}\n" for p in needed.get(name, [])))
        try:
            _git("cat-file", "-e", f"{sha}^{{commit}}", cwd=target)
        except subprocess.CalledProcessError:
            _git("fetch", "--quiet", "origin", sha, cwd=target)
        _git("checkout", "--quiet", "--detach", sha, cwd=target)
        head = _git("rev-parse", "HEAD", cwd=target)
        if head != sha:
            raise RuntimeError(f"{name}: checked out {head}, expected pinned {sha}")
        log(f"  {name:11} @ {sha[:7]}  ({len(needed.get(name, []))} paths)")
    return staging
