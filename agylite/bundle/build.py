"""Build, verify and activate the local capability bundle (P6, D-015, D-019, D-023).

Inputs: staged upstream snapshots + extraction rules + audited inventories (hashes) + pins + licenses.
Output: $AGYLITE_HOME/bundles/<bundle_id>/ with files/<repo>/<path>, third_party/<repo>/,
index.json, provenance.json, registry.yaml (P7), BUILD.json. Same inputs -> same bundle_id. A build is staged in a temporary
directory and only renamed into place (and optionally activated) when it completes; a failed build never
replaces the current bundle.
"""
import hashlib
import json
import os
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from ..paths import repo_root
from ..registry.generate import load_registry, write_registry
from ..registry.loader import cards_hash
from . import checks
from .closure import MAX_TRACE_BYTES, TEXT_EXT, trace_gaps
from .provenance import FIELDS, validate
from .rules import BUNDLED, classify, compile_rules, evidence_dir, load_capabilities, load_rules, \
    load_yaml, read_inventory
from .store import git_blob_sha1, sha256
from .transforms import TRANSFORM_VERSION, Transformer
from .transforms.ponytail import GenerateError
from .transforms.rewrites import RewriteDrift


class BuildError(RuntimeError):
    pass


def default_staging(home: Path) -> Path:
    dev = repo_root() / ".staging" / "upstream"
    return dev if dev.is_dir() else home / "staging" / "upstream"


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def compute_bundle_id(rules_path: Path, pins: dict, licenses_path: Path) -> str:
    material = json.dumps({"rules": _sha256_file(rules_path), "pins": pins, "licenses": _sha256_file(licenses_path),
                           "transforms": TRANSFORM_VERSION}, sort_keys=True)
    return hashlib.sha256(material.encode()).hexdigest()[:12]


def _load_pins(evidence: Path):
    snap = load_yaml(evidence / "upstream-staging-snapshot.yaml")["snapshots"]
    return {name: {"repo": meta["repo"], "head": meta["head"]} for name, meta in snap.items()}


def activate(home: Path, bundle_id: str):
    """Atomically point `current` at bundle_id and keep the old target as `previous`."""
    bundles = home / "bundles"
    current = bundles / "current"
    old = os.readlink(current) if current.is_symlink() else None
    if old == bundle_id:
        return
    for name, target in (("previous", old), ("current", bundle_id)):
        if target is None:
            continue
        tmp = bundles / f".{name}.tmp"
        if tmp.is_symlink() or tmp.exists():
            tmp.unlink()
        os.symlink(target, tmp)
        os.replace(tmp, bundles / name)


def list_bundles(home: Path):
    bundles = home / "bundles"
    current = os.readlink(bundles / "current") if (bundles / "current").is_symlink() else None
    out = []
    for d in sorted(p for p in bundles.glob("*") if p.is_dir() and not p.name.startswith(".") and not p.is_symlink()):
        info = json.loads((d / "BUILD.json").read_text(encoding="utf-8")) if (d / "BUILD.json").is_file() else {}
        out.append({"bundle_id": d.name, "status": info.get("status", "unknown"), "created": info.get("created"),
                    "current": d.name == current})
    return out


def verify(bundle_dir: Path):
    """Re-hash every bundled file against provenance; return a list of problems (empty = intact)."""
    problems = []
    build = json.loads((bundle_dir / "BUILD.json").read_text(encoding="utf-8"))
    if build.get("status") != "known-good":
        problems.append(f"BUILD status is {build.get('status')}")
    records = json.loads((bundle_dir / "provenance.json").read_text(encoding="utf-8"))
    for r in records:
        f = bundle_dir / r["destination_path"]
        if not f.is_file():
            problems.append(f"missing {r['destination_path']}")
        elif _sha256_file(f) != r["bundled_hash"]:
            problems.append(f"hash mismatch {r['destination_path']}")
    for repo in {r["destination_path"].split("/")[1] for r in records}:
        if not (bundle_dir / "third_party" / repo).is_dir():
            problems.append(f"license/notice files missing for {repo}")
    return problems


def _self_tests(work: Path, log):
    results = {}
    unlazy = work / "files" / "unlazy"
    if unlazy.is_dir() and shutil.which("node"):
        p = subprocess.run(["npm", "test", "--silent"], cwd=unlazy, capture_output=True, text=True)
        results["unlazy"] = {"exit": p.returncode, "ok_lines": p.stdout.count("\nok") + p.stdout.startswith("ok")}
    uiux = work / "files" / "uiuxpromax" / "src" / "ui-ux-pro-max" / "scripts"
    if uiux.is_dir():
        p = subprocess.run(["python3", "-m", "unittest", "discover", "-s", "tests"], cwd=uiux, capture_output=True, text=True)
        tail = (p.stderr.strip().splitlines() or [""])
        results["uiuxpromax"] = {"exit": p.returncode, "summary": " ".join(tail[-3:])}
    from ..runtimes import taste   # MP4 §1.4: lint exits 0 on a clean page, 1 on one with known tells
    fixtures = repo_root() / "tests" / "fixtures" / "taste"
    if taste.scripts_dir(work) and fixtures.is_dir() and (taste.node_version() or (0,))[0] >= taste.MIN_NODE:
        import tempfile
        with tempfile.TemporaryDirectory() as tmp_home:
            r = taste.self_test(work, Path(tmp_home), fixtures)
        results["taste"] = {"exit": 0 if r["ok"] else 1, "lint_exit_codes": r["exit_codes"]}
    from ..runtimes import archify, youtube   # MP5 §2.5 / §3.4: the tools score the fixtures; every example validates
    yt_fixtures = repo_root() / "tests" / "fixtures" / "youtube"
    if (work / youtube.ROOT).is_dir() and yt_fixtures.is_dir():
        r = youtube.self_test(work, yt_fixtures)
        results["youtube"] = {"exit": 0 if r["ok"] else 1, "exit_codes": r["exit_codes"]}
    if archify.cli_path(work) and (archify.node_version() or (0,))[0] >= archify.MIN_NODE:
        r = archify.self_test(work)
        results["archify"] = {"exit": 0 if r["ok"] else 1, "validated": len(r["exit_codes"]),
                              "failed": sorted(k for k, v in r["exit_codes"].items() if v)}
    for name, r in results.items():
        log(f"  self-test {name}: exit {r['exit']}")
    return results


def write_catalog(bundle: Path, staging: Path, evidence: Path, records) -> dict:
    """Plan B: index every SKILL.md of every pinned upstream into <bundle>/catalog.json (`agylite skills search`)."""
    from .. import catalog
    from ..context.sections import frontmatter
    bundled = {}
    for r in records:
        dest = r["destination_path"]
        if dest.endswith("/SKILL.md") and (bundle / dest).is_file():
            fm, _ = frontmatter((bundle / dest).read_text(encoding="utf-8", errors="replace"))
            repo = dest.split("/")[1]
            bundled[(repo, r["source_path"])] = f"{repo}/{fm.get('name') or dest.rsplit('/', 2)[-2]}"
    cat = catalog.build(staging, evidence, bundled)
    (bundle / catalog.CATALOG).write_text(json.dumps(cat, indent=1), encoding="utf-8")
    return {"skills": cat["count"], "skipped_copies": cat["skipped_copies"], "missing": len(cat["missing"])}


def build(home: Path, staging: Path | None = None, *, rules_path: Path | None = None, evidence: Path | None = None,
          licenses_path: Path | None = None, activate_bundle=True, self_test=False,
          log=print):
    home = Path(home)
    staging = Path(staging) if staging else default_staging(home)
    evidence = Path(evidence) if evidence else evidence_dir()
    rules_path = Path(rules_path) if rules_path else repo_root() / "tools" / "audit" / "extraction-rules.yaml"
    licenses_path = Path(licenses_path) if licenses_path else repo_root() / "third_party" / "licenses.json"
    rules_doc = load_rules(rules_path)
    caps = load_capabilities()
    errors = compile_rules(rules_doc, caps)
    if errors:
        raise BuildError("; ".join(errors))
    pins = _load_pins(evidence)
    licenses = json.loads(licenses_path.read_text(encoding="utf-8"))
    bundle_id = compute_bundle_id(rules_path, pins, licenses_path)
    bundles = home / "bundles"
    final = bundles / bundle_id
    if (final / "BUILD.json").is_file():
        existing = json.loads((final / "BUILD.json").read_text(encoding="utf-8"))
        if existing.get("status") == "known-good" and not verify(final):
            log(f"bundle {bundle_id} already built and intact")
            if not (final / "catalog.json").is_file():   # bundles built before Plan B gain their skill catalog
                write_catalog(final, staging, evidence, json.loads((final / "provenance.json").read_text(encoding="utf-8")))
            reg = load_registry(final)
            if reg is None or reg.get("inputs_hash") != cards_hash():
                write_registry(final)
                log("  registry regenerated from the current capability cards")
            if activate_bundle:
                activate(home, bundle_id)
            return existing

    work = bundles / f".build-{bundle_id}-{os.getpid()}"
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    inventories = {repo: read_inventory(evidence, repo) for repo in rules_doc["repos"]}
    bundled = {repo: {p[: -len(".tmpl")] if p.endswith(".tmpl") else p for p, _size, _sha in inventories[repo]
                      if classify(rules_doc["repos"][repo], p)["decision"] in BUNDLED} for repo in rules_doc["repos"]}
    transformer = Transformer(staging, inventories, bundled)
    records, index_files, capabilities = [], {}, {}
    hard, debts, notes, gaps = [], {}, {}, []
    created = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    for repo in sorted(rules_doc["repos"]):
        rr, decided, outputs = rules_doc["repos"][repo], {}, {}
        for path, _size, sha in inventories[repo]:
            rule = classify(rr, path)
            decided[path] = rule["decision"]
            if rule["decision"] not in BUNDLED:
                continue
            src = staging / repo / path
            if not src.is_file():
                raise BuildError(f"{repo}:{path} missing from staging {staging}")
            data = src.read_bytes()
            if git_blob_sha1(data) != sha:
                raise BuildError(f"{repo}:{path} does not match the audited blob hash (staging drift or tampering)")
            for extra in rule.get("inputs", []):   # a generator reads these too: same audited-hash check
                extra_sha = next((h for p, _n, h in inventories[repo] if p == extra), None)
                extra_src = staging / repo / extra
                if extra_sha is None or not extra_src.is_file() or git_blob_sha1(extra_src.read_bytes()) != extra_sha:
                    raise BuildError(f"{repo}:{extra} (input of {path}) is missing or does not match its audited hash")
            try:
                dest_rel, out, file_notes = transformer.apply(repo, path, data, rule["decision"], rule.get("capability", ""),
                                                              rule=rule, pin=pins[repo])
            except (RewriteDrift, GenerateError) as exc:
                raise BuildError(str(exc)) from exc
            # Plain single-link files (D-026): Unlazy refuses multi-link ledgers as tampering, so no hardlink dedup.
            digest = sha256(out)
            dest = f"files/{repo}/{dest_rel}"
            target = work / dest
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(out)
            cap = rule["capability"]
            domain, subdomain = cap.split("/", 1)
            records.append({
                "repository": pins[repo]["repo"], "commit_sha": pins[repo]["head"], "tag": None,
                "source_path": path, "destination_path": dest, "domain": domain, "subdomain": subdomain,
                "capability": cap, "license": licenses[repo]["license"], "attribution": licenses[repo]["attribution"],
                "integration_type": rule["decision"], "original_hash": sha, "bundled_hash": digest,
                "dependencies": [], "runtime": caps[cap]["runtime_type"], "last_verified": created[:10],
                "update_status": "pinned"})
            index_files[dest] = {"sha256": digest, "bytes": len(out), "capability": cap, "repo": repo,
                                 "source_path": path, "decision": rule["decision"], "transformed": out != data}
            capabilities.setdefault(cap, []).append(dest)
            hard += checks.hard_violations(repo, path, dest, out)
            for kind, where in checks.soft_debts(dest, rule["decision"], out):
                debts.setdefault(kind, []).append(where)
            if file_notes:
                notes[dest] = file_notes
            if os.path.splitext(path)[1].lower() in TEXT_EXT and len(out) <= MAX_TRACE_BYTES:
                outputs[path] = out.decode("utf-8", errors="ignore")
        gaps += trace_gaps(repo, decided, outputs.get, BUNDLED)
        if any(d in BUNDLED for d in decided.values()):
            for name in licenses[repo]["license_files"]:
                target = work / "third_party" / repo / name
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(staging / repo / name, target)
            if not licenses[repo]["license_files"]:
                note = work / "third_party" / repo / "ATTRIBUTION.txt"
                note.parent.mkdir(parents=True, exist_ok=True)
                note.write_text(f"{licenses[repo]['repository']} — {licenses[repo]['license']}; "
                                f"{licenses[repo]['attribution']}. {licenses[repo].get('note') or ''}\n", encoding="utf-8")

    accepted = {(a["repo"], a["target"]) for a in rules_doc.get("accepted_gaps", [])}
    open_gaps = sorted({g for g in gaps if (g[0], g[3]) not in accepted})
    problems = validate(records, caps, require_bundled_hash=True)
    errors = hard + [f"open closure gap {g[0]}:{g[1]} -> {g[3]}" for g in open_gaps] + problems
    unresolved = {dest: n for dest, n in notes.items() if any("unresolved" in x for x in n)}

    (work / "index.json").write_text(json.dumps({"bundle_id": bundle_id, "capabilities": capabilities,
                                                 "files": index_files}, indent=1, sort_keys=True), encoding="utf-8")
    (work / "provenance.json").write_text(json.dumps(records, indent=1), encoding="utf-8")
    catalog_info = write_catalog(work, staging, evidence, records)
    write_registry(work, bundle_id=bundle_id)
    info = {
        "bundle_id": bundle_id, "created": created, "status": "failed" if errors else "known-good",
        "counts": {"files": len(records), "unique_contents": len({f["sha256"] for f in index_files.values()}), "bytes": sum(f["bytes"] for f in index_files.values()),
                   "transformed": sum(f["transformed"] for f in index_files.values()),
                   "capabilities": len(capabilities)},
        "errors": errors[:200], "error_count": len(errors),
        "debts": {k: sorted(v) for k, v in debts.items()},
        "unresolved_placeholders": unresolved,
        "provenance_fields": list(FIELDS),
        "catalog": catalog_info,
    }
    if self_test and not errors:
        info["self_tests"] = _self_tests(work, log)
        if any(r["exit"] != 0 for r in info["self_tests"].values()):
            info["status"] = "failed"
            info["errors"].append("runtime self-test failed")
    (work / "BUILD.json").write_text(json.dumps(info, indent=1), encoding="utf-8")
    if final.exists():
        shutil.rmtree(final)
    os.replace(work, final)
    if info["status"] == "known-good" and activate_bundle:
        activate(home, bundle_id)
    return info
