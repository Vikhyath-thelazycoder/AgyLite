"""Explicit upstream updates with an atomic switch, rollback to a known-good bundle, and retention (P24, D-045).

update: new upstream commit → new inventory + pin (candidate evidence) → diff → build a NEW bundle (never mutate the
current one) → integrity + registry checks (+ runtime self-tests) → switch `current` only if all pass, keeping
`previous`. A failed or interrupted update leaves `current` untouched. The candidate evidence is stored inside the new
bundle (`evidence/`), so the bundle documents exactly which pins and inventories it was built from.
rollback: repoint `current` to `previous` (or a named known-good bundle); files, registry, provenance and the runtime
locks derived from them switch together because they live in one bundle directory.
gc: keep current, previous and the two newest failed builds; remove other bundles and runtimes no kept bundle uses.
"""
import json
import os
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import yaml

from ..bundle import build as bundle_build
from ..bundle.rules import BUNDLED, classify, compile_rules, evidence_dir, load_capabilities, load_rules, read_inventory
from ..bundle.store import git_blob_sha1
from ..paths import repo_root

KEEP_FAILED = 2


class UpdateError(RuntimeError):
    pass


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _pins(evidence: Path):
    return yaml.safe_load((evidence / "upstream-staging-snapshot.yaml").read_text(encoding="utf-8"))["snapshots"]


def inventory_from_dir(tree: Path):
    """(path, bytes, blob sha1) for a plain directory tree (tests, local mirrors)."""
    rows = []
    for p in sorted(tree.rglob("*")):
        if p.is_file() and ".git" not in p.relative_to(tree).parts:
            data = p.read_bytes()
            rows.append((p.relative_to(tree).as_posix(), len(data), git_blob_sha1(data)))
    return rows


def inventory_from_git(clone: Path, sha: str, repo: str | None = None):
    """(path, bytes, blob sha1) of a commit without downloading any file content: `ls-tree` without `-l` needs only
    tree objects (a blobless clone has them; `-l` would fetch every blob one by one). Sizes, used only in reports,
    come from one GitHub tree API call when available, else 0."""
    out = subprocess.run(["git", "ls-tree", "-r", sha], cwd=clone, capture_output=True, text=True, check=True).stdout
    sizes = _github_sizes(repo, sha) if repo else {}
    rows = []
    for line in out.splitlines():
        meta, path = line.split("\t", 1)
        _mode, kind, blob = meta.split()
        if kind == "blob":
            rows.append((path, sizes.get(path, 0), blob))
    return rows


def _github_sizes(repo: str, sha: str) -> dict:
    import os as _os
    import urllib.request
    if "github.com" not in _os.environ.get("AGYLITE_UPSTREAM_BASE", "https://github.com"):
        return {}
    try:
        req = urllib.request.Request(f"https://api.github.com/repos/{repo}/git/trees/{sha}?recursive=1",
                                     headers={"Accept": "application/vnd.github+json", "User-Agent": "agylite"})
        token = _os.environ.get("GITHUB_TOKEN")
        if token:
            req.add_header("Authorization", f"Bearer {token}")
        with urllib.request.urlopen(req, timeout=30) as r:
            tree = json.loads(r.read().decode())
        return {t["path"]: t.get("size", 0) for t in tree.get("tree", []) if t.get("type") == "blob"}
    except Exception:   # noqa: BLE001 - sizes are informational only
        return {}


def fetch_commit(repo: str, sha: str, target: Path, rules_repo, log=print, mirror_path: Path | None = None):
    """Blobless clone of `repo` at `sha`, sparse-checked-out to the paths the rules bundle. With a local mirror
    (P28), objects the mirror already has are reused and only the new commit's bundled blobs are downloaded."""
    from .track import url_for
    if not (target / ".git").is_dir():
        ref = ["--reference-if-able", str(mirror_path)] if mirror_path else []
        subprocess.run(["git", "clone", "--quiet", "--filter=blob:none", "--no-checkout", "--sparse", *ref,
                        url_for(repo), str(target)], check=True, capture_output=True)
    subprocess.run(["git", "fetch", "--quiet", "origin", sha], cwd=target, check=False)
    rows = inventory_from_git(target, sha, repo)
    needed = [p for p, _s, _b in rows if classify(rules_repo, p)["decision"] in BUNDLED
              or p.startswith(("LICENSE", "NOTICE", "licenses/")) or p == ".claude-plugin/plugin.json"]
    needed += [p[:-5] for p in needed if p.endswith(".tmpl")]
    subprocess.run(["git", "sparse-checkout", "set", "--no-cone", "--stdin"], cwd=target, check=True,
                   input="".join(f"/{p}\n" for p in needed), text=True)
    subprocess.run(["git", "checkout", "--quiet", "--detach", sha], cwd=target, check=True)
    log(f"  fetched {repo} @ {sha[:7]} ({len(needed)} bundled paths)")
    return rows


def _write_inventory(evidence: Path, repo: str, sha: str, rows):
    inv = evidence / "upstream-file-hashes" / f"{repo}.tsv"
    inv.parent.mkdir(parents=True, exist_ok=True)
    inv.write_text(f"# {repo} @ {sha}\nblob_sha1\tbytes\tpath\n" + "".join(f"{b}\t{s}\t{p}\n" for p, s, b in rows),
                   encoding="utf-8")


def diff_inventories(old, new, rules_repo):
    o = {p: b for p, _s, b in old}
    n = {p: b for p, _s, b in new}
    bundled = lambda p: classify(rules_repo, p)["decision"] in BUNDLED   # noqa: E731
    added = sorted(set(n) - set(o))
    removed = sorted(set(o) - set(n))
    changed = sorted(p for p in set(o) & set(n) if o[p] != n[p])
    caps = sorted({classify(rules_repo, p)["capability"] for p in added + removed + changed if bundled(p)})
    return {"added": len(added), "removed": len(removed), "changed": len(changed),
            "bundled_added": [p for p in added if bundled(p)], "bundled_removed": [p for p in removed if bundled(p)],
            "bundled_changed": [p for p in changed if bundled(p)], "capabilities_affected": caps}


def dangling_after_update(old_rows, new_rows, rules_repo, read_text) -> list:
    """Bundled files of the new commit that still reference a path the update removed (the closure trace only sees
    references to files that exist, so a deleted target needs this explicit check)."""
    from ..bundle.closure import TEXT_EXT, references, resolve
    old_files = {p for p, _s, _b in old_rows}
    new_files = {p for p, _s, _b in new_rows}
    removed = old_files - new_files
    if not removed:
        return []
    old_dirs = {p.rsplit("/", i)[0] for p in old_files for i in range(1, p.count("/") + 1)}
    out = []
    for path in sorted(new_files):
        if classify(rules_repo, path)["decision"] not in BUNDLED or os.path.splitext(path)[1].lower() not in TEXT_EXT:
            continue
        text = read_text(path)
        for ref in references(text or "", path):
            target = resolve(ref, path, old_files, old_dirs)
            if target in removed:
                out.append(f"dangling reference after update: {path} -> {target} (removed upstream)")
    return out


def update(home: Path, repo: str, sha: str, *, source: Path | None = None, staging: Path | None = None,
           evidence: Path | None = None, rules_path: Path | None = None, licenses_path: Path | None = None,
           self_test=False, check_registry=True, mirror_path: Path | None = None, log=print) -> dict:
    """Build and (if every check passes) activate a bundle with `repo` pinned at `sha`.
    `source`: a local tree of the new commit (tests / offline mirrors); otherwise the commit is fetched (network)."""
    home = Path(home)
    evidence = Path(evidence) if evidence else _current_evidence(home)
    staging = Path(staging) if staging else bundle_build.default_staging(home)
    rules_path = Path(rules_path) if rules_path else repo_root() / "tools" / "audit" / "extraction-rules.yaml"
    rules_doc = load_rules(rules_path)
    compile_rules(rules_doc, load_capabilities())
    pins = _pins(evidence)
    if repo not in pins or repo not in rules_doc["repos"]:
        raise UpdateError(f"unknown upstream {repo}; known: {', '.join(sorted(pins))}")
    if len(sha) != 40 or any(c not in "0123456789abcdef" for c in sha):
        raise UpdateError("pin updates to a full 40-character commit SHA (tags and branches move)")
    old_id = os.readlink(home / "bundles" / "current") if (home / "bundles" / "current").is_symlink() else None
    work = home / "updates" / f"{repo}-{sha[:12]}"
    shutil.rmtree(work, ignore_errors=True)
    cand_ev, cand_stage = work / "evidence", work / "staging"
    shutil.copytree(evidence, cand_ev)
    cand_stage.mkdir(parents=True)
    trees = home / "staging-current"   # trees of upstreams already moved by earlier updates (match their pins)
    for name in pins:   # every other upstream: the tree that matches its current pin
        src = trees / name if (trees / name).exists() else staging / name
        if name != repo and src.exists():
            (cand_stage / name).symlink_to(src.resolve())
    if source is not None:
        shutil.copytree(source, cand_stage / repo, symlinks=False)
        rows = inventory_from_dir(cand_stage / repo)
    else:
        rows = fetch_commit(pins[repo]["repo"], sha, cand_stage / repo, rules_doc["repos"][repo], log, mirror_path)
    old_rows = read_inventory(evidence, repo)
    report = {"repo": repo, "from": pins[repo]["head"], "to": sha, "at": _now(), "previous_bundle": old_id,
              "diff": diff_inventories(old_rows, rows, rules_doc["repos"][repo])}

    def read_new(path):
        f = cand_stage / repo / path
        return f.read_text(encoding="utf-8", errors="ignore") if f.is_file() else None
    dangling = dangling_after_update(old_rows, rows, rules_doc["repos"][repo], read_new)
    if dangling:
        report.update(status="failed", errors=dangling[:50])
        _log(home, report)
        return report
    _write_inventory(cand_ev, repo, sha, rows)
    snap = yaml.safe_load((cand_ev / "upstream-staging-snapshot.yaml").read_text(encoding="utf-8"))
    snap["snapshots"][repo]["head"] = sha
    (cand_ev / "upstream-staging-snapshot.yaml").write_text(yaml.safe_dump(snap, sort_keys=True), encoding="utf-8")
    try:
        info = bundle_build.build(home, cand_stage, rules_path=rules_path, evidence=cand_ev,
                                  licenses_path=licenses_path, activate_bundle=False, self_test=self_test, log=log)
    except bundle_build.BuildError as exc:
        report.update(status="failed", errors=[str(exc)])
        _log(home, report)
        return report
    bundle = home / "bundles" / info["bundle_id"]
    problems = list(info["errors"]) if info["status"] != "known-good" else []
    if not problems:
        problems += bundle_build.verify(bundle)
        if check_registry:
            from ..registry.generate import check as registry_check
            reg = registry_check(bundle_dir=bundle)
            # CARD.md shows bundled-file counts; new upstream files make it stale until `registry cards` regenerates
            # it in the same change (CI does), so that alone is a warning, not a failure.
            report["warnings"] = [p for p in reg if "CARD.md is stale" in p]
            problems += [p for p in reg if "CARD.md is stale" not in p]
    shutil.copytree(cand_ev, bundle / "evidence", dirs_exist_ok=True)
    report.update(bundle_id=info["bundle_id"], counts=info["counts"], errors=problems[:50],
                  status="activated" if not problems else "failed")
    if not problems:
        bundle_build.activate(home, info["bundle_id"])
        trees.mkdir(parents=True, exist_ok=True)   # later updates build with this upstream's new tree
        link = trees / repo
        if link.is_symlink() or link.exists():
            link.unlink()
        link.symlink_to((cand_stage / repo).resolve())
    _log(home, report)
    return report


def _current_evidence(home: Path) -> Path:
    cur = home / "bundles" / "current"
    own = cur / "evidence"
    return own if own.is_dir() else evidence_dir()


def _log(home: Path, report):
    d = Path(home) / "updates"
    d.mkdir(parents=True, exist_ok=True)
    with open(d / "history.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(report) + "\n")


def rollback(home: Path, to: str | None = None) -> dict:
    home = Path(home)
    bundles = home / "bundles"
    cur = os.readlink(bundles / "current") if (bundles / "current").is_symlink() else None
    target = to or (os.readlink(bundles / "previous") if (bundles / "previous").is_symlink() else None)
    if not target:
        raise UpdateError("no previous bundle to roll back to (name one with --to)")
    if target == cur:
        raise UpdateError(f"{target} is already current")
    path = bundles / target
    if not path.is_dir():
        raise UpdateError(f"bundle {target} not found")
    problems = bundle_build.verify(path)
    if problems:
        raise UpdateError(f"bundle {target} is not known-good and intact: {problems[0]}")
    bundle_build.activate(home, target)
    report = {"rollback": True, "from": cur, "to": target, "at": _now()}
    _log(home, report)
    return report


def gc(home: Path, dry_run=False) -> dict:
    """Keep current, previous, and the newest KEEP_FAILED failed builds; drop other bundles and orphaned runtimes."""
    home = Path(home)
    bundles = home / "bundles"
    keep = {os.readlink(bundles / n) for n in ("current", "previous") if (bundles / n).is_symlink()}
    listed = bundle_build.list_bundles(home)
    failed = sorted((b for b in listed if b["status"] != "known-good"), key=lambda b: b["created"] or "", reverse=True)
    keep |= {b["bundle_id"] for b in failed[:KEEP_FAILED]}
    drop = [b["bundle_id"] for b in listed if b["bundle_id"] not in keep]
    locks = set()
    from ..runtimes import venv as pyvenv
    for bid in keep:
        files = bundles / bid / "files"
        for repo, prefix in (("graphify", "graphify"), ("beyondseo", "seo"), ("brag", "brag")):
            src = files / repo if repo != "brag" else files / "brag" / "skills" / "brag" / "scripts"
            if (src / "pyproject.toml").is_file():
                locks.add(f"{prefix}-{pyvenv.lock_of(src, repo)}")
    runtimes = home / "runtimes"
    stale_rt = sorted(d.name for d in runtimes.iterdir() if d.is_dir() and d.name not in locks) if runtimes.is_dir() else []
    partial = sorted(p.name for p in bundles.glob(".build-*") if p.is_dir())   # interrupted builds
    if not dry_run:
        for name in partial:
            shutil.rmtree(bundles / name, ignore_errors=True)
        for bid in drop:
            shutil.rmtree(bundles / bid, ignore_errors=True)
        for name in stale_rt:
            shutil.rmtree(runtimes / name, ignore_errors=True)
    return {"kept": sorted(keep), "removed_bundles": drop, "removed_runtimes": stale_rt, "removed_partial_builds": partial,
            "dry_run": dry_run}
