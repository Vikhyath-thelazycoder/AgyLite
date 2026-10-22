"""Generate the capability registry and L1 cards (P7, spec §13, §16).

registry.yaml = authored cards (capabilities/**/card.yaml, merged with defaults) + provenance-derived fields
(source_repositories, source_paths, commit_sha, license, integration_type, version, token_cost_estimate).
One registry is written into each bundle; `plan` mode derives the same registry from the audited extraction plan so
the repository can be checked without a built bundle (CI).

CARD.md (L1 summary, ≤ CARD_MAX_BYTES ≈ 250 est. tokens) is rendered from the card, so the card stays the only
authored source; `check` fails when a committed CARD.md is stale.
"""
import hashlib
import json
from pathlib import Path

import yaml

from .. import __version__
from . import loader, schema

CARD_MAX_BYTES = 1000  # ≈ 250 estimated tokens at bytes/4 (spec §46 estimate)
REGISTRY_FILE = "registry.yaml"
ENTRY_POINT_FILES = {"SKILL.md", "SKILL.md.tmpl"}


def upstream_names(evidence: Path | None = None):
    from ..bundle.provenance import load_pins
    pins = load_pins(evidence)
    return sorted(set(pins) | {p["repo"] for p in pins.values()})


def entries_from_plan():
    """One entry per file the extraction rules select (sizes/hashes from the audited inventories)."""
    from ..bundle.provenance import planned_records
    from ..bundle.rules import evidence_dir, read_inventory
    sizes = {}
    out = []
    for r in planned_records(verified_on="plan"):
        repo = r["destination_path"].split("/")[2]
        if repo not in sizes:
            sizes[repo] = {p: n for p, n, _ in read_inventory(evidence_dir(), repo)}
        out.append({"capability": r["capability"], "repo": repo, "repository": r["repository"],
                    "commit_sha": r["commit_sha"], "license": r["license"], "source_path": r["source_path"],
                    "decision": r["integration_type"], "hash": r["original_hash"], "bytes": sizes[repo][r["source_path"]]})
    return out


def entries_from_bundle(bundle_dir: Path):
    """One entry per bundled file, from the bundle's own provenance and index (bytes after transforms)."""
    records = json.loads((bundle_dir / "provenance.json").read_text(encoding="utf-8"))
    files = json.loads((bundle_dir / "index.json").read_text(encoding="utf-8"))["files"]
    return [{"capability": r["capability"], "repo": r["destination_path"].split("/")[1],
             "repository": r["repository"], "commit_sha": r["commit_sha"], "license": r["license"],
             "source_path": r["source_path"], "decision": r["integration_type"], "hash": r["bundled_hash"],
             "bytes": files[r["destination_path"]]["bytes"]} for r in records]


def _by_capability(entries):
    out = {}
    for e in entries:
        out.setdefault(e["capability"], []).append(e)
    return out


def _entry_points(entries, exclude):
    names = set()
    for e in entries:
        parts = e["source_path"].split("/")
        if parts[-1] in ENTRY_POINT_FILES and len(parts) > 1:
            names.add(parts[-2])
        elif len(parts) > 1 and parts[-2] == "agents" and parts[-1].endswith(".md"):
            names.add(parts[-1][:-3])
    return sorted(n for n in names if n.lower() not in exclude)


def _sentence(text):
    text = text.strip()
    return text if text[-1:] in ".!?" else text + "."


def render_card_md(cid, card, entries, deps_with_files=(), exclude=()):
    """L1 summary for one capability: what it is, when it activates, what it loads, what done means."""
    act = card["activation_conditions"]
    tags = card["intent_tags"]
    use_when = ", ".join(tags[:8]) + (" …" if len(tags) > 8 else "") if tags else "; ".join(act["when"])
    needs = [f"runtime {card['runtime_type']}"]
    if card["requires_network"] is not False:
        needs.append(f"network {'yes' if card['requires_network'] is True else card['requires_network']}")
    if card["requires_browser"] != "none":
        needs.append(f"browser {card['requires_browser']}")
    if card["requires_codebase_analysis"]:
        needs.append("codebase analysis first")
    if entries:
        excluded = {n.lower() for n in exclude} | {n.split("/")[-1].lower() for n in exclude}
        points = _entry_points(entries, excluded)
        shown = ", ".join(points[:6]) + (f" (+{len(points) - 6} more)" if len(points) > 6 else "")
        loads = f"{len(entries)} bundled files" + (f"; entry points: {shown}" if points else "")
    elif deps_with_files:
        loads = "shares the bundled files of " + ", ".join(deps_with_files)
    else:
        loads = "OS-native (no bundled files)"
    if card.get("guide"):   # MP5 §1.4: the authored guide is the primary skill
        domain, sub = cid.split("/", 1)
        loads = f"Agylite guide (skill agylite/{domain}-{sub})" + ("" if loads.startswith("OS-native") else f"; {loads}")
    lines = [
        f"# {cid} — {card['name']}", "",
        _sentence(card["description"]), "",
        f"- **Use when:** {use_when}",
        f"- **Activation:** {act['mode']} · priority {card['priority']} · context {card['context_level']}"
        + ("" if card["enabled"] else f" · {card.get('runtime_status') or 'DISABLED'}"),
        f"- **Needs:** {'; '.join(needs)}",
        f"- **Loads:** {loads}",
        f"- **Done means:** {' · '.join(card['verification_requirements'])}",
    ]
    if card.get("web_qa_class"):
        modes = card.get("web_qa_modes") or {}
        lines.append(f"- **Web QA class:** {card['web_qa_class']}"
                     + (" (" + ", ".join(f"{k} {v}" for k, v in modes.items()) + ")" if modes else ""))
    related = ", ".join(card["related_capabilities"]) or "—"
    lines.append(f"- **Related:** {related} · **Fallback:** {card['fallback_capability'] or '—'}")
    return "\n".join(lines) + "\n"


def card_docs(cards, entries, exclude=()):
    grouped = _by_capability(entries)
    return {cid: render_card_md(cid, card, grouped.get(cid, []),
                                [d for d in card["dependencies"] if grouped.get(d)], exclude)
            for cid, card in cards.items()}


def write_card_docs(root: Path | None = None):
    """Render every CARD.md from its card and the extraction plan; return the ids whose file changed."""
    cards = loader.load_cards(root)
    changed = []
    for cid, text in card_docs(cards, entries_from_plan(), upstream_names()).items():
        path = loader.capabilities_dir(root) / cid / "CARD.md"
        if not path.is_file() or path.read_text(encoding="utf-8") != text:
            path.write_text(text, encoding="utf-8")
            changed.append(cid)
    return changed


def _version(card, entries):
    material = json.dumps({"card": card, "files": sorted((e["repo"], e["source_path"], e["hash"]) for e in entries)},
                          sort_keys=True, default=str)
    return hashlib.sha256(material.encode()).hexdigest()[:12]


def generate(cards, entries, *, domains, source, bundle_id=None, inputs_hash=None, card_bytes=None):
    """Registry document: every §13 field for every capability, in spec order."""
    grouped = _by_capability(entries)
    card_bytes = card_bytes or {}
    capabilities = {}
    for cid, card in cards.items():
        own = grouped.get(cid, [])
        domain, subdomain = cid.split("/", 1)
        repos = sorted({e["repository"] for e in own})
        first = {r: next(e for e in own if e["repository"] == r) for r in repos}
        decisions = sorted({e["decision"] for e in own})
        if card["origin"] in ("os-native", "mixed"):
            decisions.append("OS_NATIVE")
        nbytes = sum(e["bytes"] for e in own)
        derived = {
            "capability_id": cid, "domain": domain, "subdomain": subdomain,
            "source_repositories": repos,
            "source_paths": {r: sorted(e["source_path"] for e in own if e["repository"] == r) for r in repos},
            "version": _version(card, own),
            "commit_sha": {r: first[r]["commit_sha"] for r in repos},
            "license": {r: first[r]["license"] for r in repos},
            "integration_type": decisions,
            "token_cost_estimate": {
                "card_l1": -(-card_bytes.get(cid, 0) // 4), "bundled_files": len(own), "bundled_bytes": nbytes,
                "bundled_tokens": nbytes // 4, "method": "bytes/4 estimate (spec §46)"},
        }
        merged = {**card, **derived}
        entry = {f: merged[f] for f in schema.SPEC_FIELDS}
        entry.update({f: card[f] for f in schema.EXTRA_FIELDS if f in card})
        entry.setdefault("runtime_status", "ACTIVE")  # D-035: every entry states whether policy disables it
        capabilities[cid] = entry
    return {"registry_version": 1, "os_version": __version__, "source": source, "bundle_id": bundle_id,
            "inputs_hash": inputs_hash,
            "domains": {d: {"purpose": m["purpose"], "capabilities": m["capabilities"]} for d, m in domains.items()},
            "capabilities": capabilities}


def _card_bytes(cards, root):
    out = {}
    for cid in cards:
        path = loader.capabilities_dir(root) / cid / "CARD.md"
        out[cid] = path.stat().st_size if path.is_file() else 0
    return out


def plan_registry(root: Path | None = None, entries=None):
    cards = loader.load_cards(root)
    return generate(cards, entries if entries is not None else entries_from_plan(), domains=loader.load_domains(root), source="plan",
                    inputs_hash=loader.cards_hash(root), card_bytes=_card_bytes(cards, root))


def write_registry(bundle_dir: Path, root: Path | None = None, bundle_id: str | None = None):
    """Generate registry.yaml for one bundle from its provenance (called by `bundle build` and `registry build`)."""
    cards = loader.load_cards(root)
    reg = generate(cards, entries_from_bundle(bundle_dir), domains=loader.load_domains(root), source="bundle",
                   bundle_id=bundle_id or bundle_dir.name, inputs_hash=loader.cards_hash(root),
                   card_bytes=_card_bytes(cards, root))
    tmp = bundle_dir / f".{REGISTRY_FILE}.tmp"
    tmp.write_text(yaml.safe_dump(reg, sort_keys=False, allow_unicode=True, width=120), encoding="utf-8")
    tmp.replace(bundle_dir / REGISTRY_FILE)
    return reg


def load_registry(bundle_dir: Path):
    path = bundle_dir / REGISTRY_FILE
    if not path.is_file():
        return None
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def check(root: Path | None = None, bundle_dir: Path | None = None):
    """All registry problems: structure, cards, extraction-rule references, CARD.md freshness/size, generated
    registry completeness, and (when a bundle is given) that its registry.yaml is present, current and valid."""
    from ..bundle.rules import compile_rules, load_rules
    problems = loader.structure_problems(root)
    try:
        cards = loader.load_cards(root)
    except loader.RegistryError as exc:
        return problems + [str(exc)]
    problems += schema.validate_cards(cards)
    problems += [f"{cid}: guide {card['guide']} missing next to card.yaml" for cid, card in cards.items()
                 if card.get("guide") and not (loader.capabilities_dir(root) / cid / card["guide"]).is_file()]
    problems += [f"extraction rules: {e}" for e in compile_rules(load_rules(), cards)]
    names, entries = upstream_names(), entries_from_plan()
    for cid, text in card_docs(cards, entries, names).items():
        path = loader.capabilities_dir(root) / cid / "CARD.md"
        if not path.is_file():
            problems.append(f"{cid}: CARD.md missing (run `agylite registry cards`)")
        elif path.read_text(encoding="utf-8") != text:
            problems.append(f"{cid}: CARD.md is stale (run `agylite registry cards`)")
        if len(text.encode()) > CARD_MAX_BYTES:
            problems.append(f"{cid}: CARD.md is {len(text.encode())} bytes (> {CARD_MAX_BYTES}, ≈250 est. tokens)")
    if problems:
        return problems
    problems += schema.validate_registry(plan_registry(root, entries), names)
    if bundle_dir is not None:
        reg = load_registry(bundle_dir)
        if reg is None:
            problems.append(f"bundle {bundle_dir.name}: {REGISTRY_FILE} missing (run `agylite registry build`)")
        elif reg.get("inputs_hash") != loader.cards_hash(root):
            problems.append(f"bundle {bundle_dir.name}: {REGISTRY_FILE} is stale (run `agylite registry build`)")
        else:
            problems += [f"bundle {bundle_dir.name}: {p}" for p in schema.validate_registry(reg, names)]
        problems += sources_priority_problems(cards, bundle_dir)
    return problems


def sources_priority_problems(cards, bundle_dir: Path):
    """MP1 F5: every sources_priority glob must match a file the bundle maps to that capability, so a source removed
    or moved upstream fails the check instead of silently falling back to another file. MP4 §1.5: an exact path (no
    wildcard) may name a file bundled under another capability (e.g. Taste's SKILL.md leads two capabilities)."""
    import fnmatch
    index = json.loads((bundle_dir / "index.json").read_text(encoding="utf-8"))
    files = index.get("files") or {}
    by_cap = {}
    for path, meta in files.items():
        by_cap.setdefault(meta.get("capability"), []).append(path)
    exact = lambda g: not any(ch in g for ch in "*?[")   # noqa: E731
    return [f"{cid}: sources_priority {g} matches no file of {cid} in bundle {bundle_dir.name}"
            for cid, card in cards.items() for g in card.get("sources_priority") or []
            if not any(fnmatch.fnmatchcase(p, g) for p in by_cap.get(cid, [])) and not (exact(g) and g in files)]
