"""Provenance records (spec §36): one per bundled upstream file.

P5 builds the *planned* records from the audit evidence (rules + per-file hashes + pins + licenses).
P6 fills `bundled_hash` and `dependencies` when it writes the bundle.
"""
import json
import re
from datetime import date
from pathlib import Path

from ..paths import repo_root
from .rules import (BUNDLED, classify, compile_rules, evidence_dir, load_capabilities,
                    load_rules, load_yaml, read_inventory)

FIELDS = ("repository", "commit_sha", "tag", "source_path", "destination_path", "domain", "subdomain", "capability",
          "license", "attribution", "integration_type", "original_hash", "bundled_hash", "dependencies", "runtime",
          "last_verified", "update_status")
SHA1 = re.compile(r"^[0-9a-f]{40}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")


def licenses_file() -> Path:
    return repo_root() / "third_party" / "licenses.json"


def load_licenses(path: Path | None = None):
    with open(path or licenses_file(), encoding="utf-8") as f:
        return json.load(f)


def load_pins(evidence: Path | None = None):
    snap = load_yaml((evidence or evidence_dir()) / "upstream-staging-snapshot.yaml")["snapshots"]
    return {name: {"repo": meta["repo"], "head": meta["head"]} for name, meta in snap.items()}


def planned_records(verified_on: str | None = None):
    """Provenance for every file the extraction rules select for the bundle."""
    rules_doc = load_rules()
    caps = load_capabilities()
    errors = compile_rules(rules_doc, caps)
    if errors:
        raise ValueError("; ".join(errors))
    pins, licenses, evidence = load_pins(), load_licenses(), evidence_dir()
    verified_on = verified_on or date.today().isoformat()
    records = []
    for repo in sorted(rules_doc["repos"]):
        rr = rules_doc["repos"][repo]
        for path, _size, sha in read_inventory(evidence, repo):
            rule = classify(rr, path)
            if rule["decision"] not in BUNDLED:
                continue
            cap = rule["capability"]
            domain, subdomain = cap.split("/", 1)
            records.append({
                "repository": pins[repo]["repo"],
                "commit_sha": pins[repo]["head"],
                "tag": None,
                "source_path": path,
                "destination_path": f"{cap}/{repo}/{rule.get('output', path)}",
                "domain": domain,
                "subdomain": subdomain,
                "capability": cap,
                "license": licenses[repo]["license"],
                "attribution": licenses[repo]["attribution"],
                "integration_type": rule["decision"],
                "original_hash": sha,
                "bundled_hash": None,
                "dependencies": [],
                "runtime": caps[cap]["runtime_type"],
                "last_verified": verified_on,
                "update_status": "pinned",
            })
    return records


def validate(records, caps, *, require_bundled_hash=False):
    """Return a list of human-readable problems (empty = valid)."""
    problems = []
    seen = set()
    for i, r in enumerate(records):
        where = f"record {i} ({r.get('repository')}:{r.get('source_path')})"
        missing = [f for f in FIELDS if f not in r]
        if missing:
            problems.append(f"{where}: missing fields {missing}")
            continue
        if not SHA1.match(str(r["commit_sha"])):
            problems.append(f"{where}: commit_sha is not a 40-hex SHA")
        if not SHA1.match(str(r["original_hash"])):
            problems.append(f"{where}: original_hash is not a git blob SHA-1")
        if require_bundled_hash and not SHA256.match(str(r["bundled_hash"])):
            problems.append(f"{where}: bundled_hash is not a sha256")
        if r["integration_type"] not in BUNDLED:
            problems.append(f"{where}: integration_type {r['integration_type']} is not a bundled decision")
        if r["capability"] not in caps or r["capability"] != f"{r['domain']}/{r['subdomain']}":
            problems.append(f"{where}: unknown or inconsistent capability {r['capability']}")
        if not r["license"] or not r["attribution"]:
            problems.append(f"{where}: license/attribution empty")
        if r["destination_path"] in seen:
            problems.append(f"{where}: duplicate destination_path")
        seen.add(r["destination_path"])
    return problems
