"""`agylite doctor`: Python port of scripts/doctor (v1.0.1) plus environment checks."""
import json
import sys
from pathlib import Path

from . import Report

PORTABLE_SCHEMA = "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json"
STRUCTURE_DIRS = ["skills", "agents", "capabilities", "config", "tests", "scripts", ".codex-plugin",
                  ".claude-plugin", ".agents/skills", ".agents/plugins", ".github/workflows"]
KEY_FILES = ["README.md", "AGENTS.md", "CLAUDE.md", "LICENSE", "CHANGELOG.md", "CONTRIBUTING.md", "SECURITY.md",
             "CODE_OF_CONDUCT.md"]


def _json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _yaml_ok(path: Path):
    import yaml
    try:
        yaml.safe_load(path.read_text(encoding="utf-8"))
        return True
    except (OSError, yaml.YAMLError):
        return False


def _marketplace_ok(data):
    try:
        plugin = data["plugins"][0]
        return plugin["name"] == "agylite" and plugin["source"] == "./"
    except (TypeError, KeyError, IndexError):
        return False


def _contains(paths, needle):
    for p in paths:
        files = [p] if p.is_file() else list(p.rglob("*")) if p.is_dir() else []
        for f in files:
            if f.is_file() and needle in f.read_text(encoding="utf-8", errors="ignore"):
                return True
    return False


# MP1 F9: a pin is stale relative to how often its upstream is tracked (config/upstreams.yaml); manual never warns.
STALE_PIN_DAYS = {"weekly": 14, "monthly": 45, "releases": 45, "manual": None}


def pin_dates(root: Path) -> dict:
    """{upstream: date its pin last changed}: the last commit of its audited inventory in this checkout, else the
    snapshot's capture date (an installed copy has no git history)."""
    import re
    import subprocess
    from datetime import date
    evidence = root / "docs" / "audit" / "evidence"
    snap = evidence / "upstream-staging-snapshot.yaml"
    m = re.search(r"^# Captured: (\d{4}-\d{2}-\d{2})", snap.read_text(encoding="utf-8"), re.M) if snap.is_file() else None
    captured = date.fromisoformat(m.group(1)) if m else None
    out = {}
    for inv in sorted((evidence / "upstream-file-hashes").glob("*.tsv")):
        try:
            day = subprocess.run(["git", "log", "-1", "--format=%cs", "--", str(inv.relative_to(root))], cwd=root,
                                 capture_output=True, text=True, timeout=10).stdout.strip()
        except (OSError, subprocess.SubprocessError):
            day = ""
        when = date.fromisoformat(day) if day else captured
        if when:
            out[inv.stem] = when
    return out


def pin_age_lines(dates: dict, policy: dict, today) -> list:
    """[(level, message)]: the oldest pin per tracking policy, warned when older than that policy allows."""
    lines = []
    for track in ("weekly", "monthly", "releases", "manual"):
        repos = [n for n in dates if policy.get(n, {}).get("track", "weekly") == track]
        if not repos:
            continue
        oldest = min(repos, key=lambda n: (dates[n], n))
        age, limit = (today - dates[oldest]).days, STALE_PIN_DAYS[track]
        text = f"{track} pins: oldest {oldest}, {age} days ({dates[oldest].isoformat()})"
        if limit is None:
            lines.append(("ok", f"{text}; manual upstreams are never due"))
        elif age > limit:
            stale = sorted(n for n in repos if (today - dates[n]).days > limit)
            lines.append(("warn", f"{text} > {limit}: review {', '.join(stale)} with `agylite update --check`"))
        else:
            lines.append(("ok", f"{text}; review after {limit} days"))
    return lines


def _checked(home: Path) -> dict:
    """{upstream: ISO time an update check last found it current or applied it} from the tracking state."""
    state = home / "updates" / "tracking.json"
    try:
        data = json.loads(state.read_text(encoding="utf-8")) if state.is_file() else {}
    except ValueError:
        return {}
    out = {}
    for n, v in data.items():
        stamps = [v.get(k) for k in ("applied_check", "checked_current")] if isinstance(v, dict) else []
        stamps = sorted(s for s in stamps if s)
        if stamps:
            out[n] = stamps[-1]
    return out


def fresh_dates(dates: dict, home: Path) -> dict:
    """A pin is as fresh as the later of its last change and the last check that found it current."""
    from datetime import date
    checked = _checked(home)
    return {n: max(d, date.fromisoformat(checked[n][:10])) if n in checked else d for n, d in dates.items()}


def last_update_run(home: Path):
    """Date of the newest `agylite update --check|--latest` run recorded in the tracking state, else None."""
    stamps = sorted(_checked(home).values())
    return stamps[-1][:10] if stamps else None


def skill_owned_copy(bundle_dir: Path, path: str) -> bool:
    """True when `path` sits in a skill's references/ and that skill's own SKILL.md links it skill-relatively, so the
    copy is part of a whole skill, not an accidental duplicate (MP1 F12)."""
    head, sep, rest = path.partition("/references/")
    skill = bundle_dir / head / "SKILL.md"
    return bool(sep) and skill.is_file() and f"references/{rest}" in skill.read_text(encoding="utf-8", errors="ignore")


def host_and_supply_checks(r, root: Path, user_home: Path, bundle_dir):
    """P25 (§59, MR-02/03, doc 22 §7): separately installed upstream plugins and their always-loaded cost, host MCP /
    Chrome DevTools servers, stale pins, duplicate design files. Reads names and sizes only, never secret values."""
    from datetime import date

    from .benchmark import NAME, installed_plugins, measure_plugin
    r.section("🧩 Host Environment")
    seen = set()
    for name, version, path in installed_plugins(user_home / ".claude" / "plugins"):
        if name in seen or name.startswith(NAME + "@"):
            continue
        seen.add(name)
        cost = sum(b for _, b in measure_plugin(path).values())
        r.warn(f"{name} {version} is installed separately: ~{cost // 4:,} est. tokens of descriptions every turn "
               "(its selected content is already in the bundle)")
        for mcp in list(path.glob(".mcp.json")) + list(path.glob("*/.mcp.json")):
            try:
                servers = (json.loads(mcp.read_text(encoding="utf-8")).get("mcpServers") or {})
            except ValueError:
                servers = {}
            for sname in servers:
                hint = " — browser automation; the OS never uses it (config/verification.yaml)" \
                    if "chrome" in sname.lower() or "playwright" in sname.lower() or "browser" in sname.lower() else ""
                r.warn(f"host MCP server '{sname}' enabled by plugin {name}{hint}")
    user_cfg = user_home / ".claude.json"
    if user_cfg.is_file():
        try:
            names = list((json.loads(user_cfg.read_text(encoding="utf-8")).get("mcpServers") or {}))
        except ValueError:
            names = []
        for sname in names:
            r.warn(f"host MCP server '{sname}' configured in ~/.claude.json (outside the OS; the OS adds none)")
    if not seen:
        r.ok("No separately installed upstream plugins")
    r.end_section()

    r.section("📌 Supply Chain")
    from ..paths import agylite_home
    from ..update.track import load_policy
    dates = fresh_dates(pin_dates(root), agylite_home())
    for level, message in pin_age_lines(dates, load_policy(root), date.today()):
        (r.warn if level == "warn" else r.ok)(message)
    last = last_update_run(agylite_home())
    r.ok(f"Last `agylite update --check`/`--latest` run on this machine: {last or 'never'}")
    if bundle_dir is not None and (bundle_dir / "index.json").is_file():
        files = json.loads((bundle_dir / "index.json").read_text(encoding="utf-8"))["files"]
        by_hash = {}
        for dest, meta in files.items():
            if meta["capability"].startswith("design/") and dest.endswith(".md"):
                by_hash.setdefault(meta["sha256"], []).append(dest)
        dups = [v for v in by_hash.values() if len(v) > 1]
        own = [v for v in dups if all(skill_owned_copy(bundle_dir, p) for p in v)]
        accidental = [v for v in dups if v not in own]
        if accidental:
            r.warn(f"{len(accidental)} design rule files are bundled more than once with identical content "
                   f"(e.g. {accidental[0][0]}); the context engine loads one copy")
        else:
            r.ok("No duplicate design rule files in the bundle")
        if own:
            r.ok(f"{len(own)} identical reference file(s) kept once per skill that links it (whole skills, "
                 f"IMPLEMENTATION_PLAN §2.1; e.g. {own[0][0]})")
    r.end_section()


def run(root: Path, user_home: Path | None = None) -> int:
    """Doctor with every line passed through the redactor (§78: no secrets in diagnostics output)."""
    import contextlib
    import io

    from ..events.redact import redact_text
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = _run(root, user_home or Path.home())
    print(redact_text(buf.getvalue()), end="")
    return code


def _run(root: Path, user_home: Path) -> int:
    r = Report("🔍 Agylite — Doctor")

    r.section("🐍 Environment")
    r.check(sys.version_info >= (3, 10), f"Python {sys.version.split()[0]} (>= 3.10)",
            f"Python {sys.version.split()[0]} is older than 3.10")
    try:
        import yaml  # noqa: F401
        r.ok("PyYAML importable")
    except ImportError:
        r.fail("PyYAML missing — install with `pip install -e .`")
        r.end_section()
        print(f"Results: ✅ {r.passed} passed, ❌ {r.failed} failed, ⚠️  {r.warned} warnings")
        return 1
    r.end_section()

    r.section("📁 Repository Structure")
    for d in STRUCTURE_DIRS:
        r.check((root / d).is_dir(), f"{d}/ exists", f"{d}/ missing")
    r.end_section()

    r.section("📦 Portable Root Manifest (Agent Plugins 1.0.0)")
    data = _json(root / "plugin.json")
    if data is None:
        r.fail("plugin.json (root portable manifest) missing or invalid")
    else:
        forbidden = [f for f in ("skills", "mcpServers", "interface", "hooks", "tools") if f in data]
        valid = (data.get("$schema") == PORTABLE_SCHEMA and data.get("name") == "agylite"
                 and all(k in data for k in ("version", "description", "author", "license")) and not forbidden)
        r.check(valid, "plugin.json conforms to Agent Plugins 1.0.0 schema",
                "plugin.json validation failed (invalid schema or forbidden top-level fields)")
    r.end_section()

    r.section("📋 Host Manifests & Marketplaces")
    codex = _json(root / ".codex-plugin/plugin.json")
    r.check(codex is not None and "mcpServers" not in codex, ".codex-plugin/plugin.json valid JSON (no MCP)",
            ".codex-plugin/plugin.json missing, invalid or contains MCP")
    claude = _json(root / ".claude-plugin/plugin.json")
    r.check(claude is not None and "mcpServers" not in claude and "skills" not in claude,
            ".claude-plugin/plugin.json valid minimal JSON", ".claude-plugin/plugin.json invalid or contains non-standard fields")
    r.check(_marketplace_ok(_json(root / ".agents/plugins/marketplace.json")), ".agents/plugins/marketplace.json valid",
            ".agents/plugins/marketplace.json missing or invalid")
    r.check(_marketplace_ok(_json(root / ".claude-plugin/marketplace.json")), ".claude-plugin/marketplace.json valid",
            ".claude-plugin/marketplace.json missing or invalid")
    r.end_section()

    r.section("🌌 Antigravity Packaging")
    skill = root / ".agents/skills/agylite/SKILL.md"
    r.check(skill.is_file() and "name: agylite" in skill.read_text(encoding="utf-8"),
            ".agents/skills/agylite/SKILL.md adapter intact", ".agents/skills/agylite/SKILL.md missing or unnamed")
    r.end_section()

    r.section("⚙️  CI Workflow Integrity")
    import yaml
    ci = root / ".github/workflows/ci.yml"
    try:
        ci_data = yaml.safe_load(ci.read_text(encoding="utf-8"))
        ci_ok = isinstance(ci_data, dict) and "name" in ci_data and "jobs" in ci_data
    except (OSError, yaml.YAMLError):
        ci_ok = False
    r.check(ci_ok, ".github/workflows/ci.yml valid YAML workflow", ".github/workflows/ci.yml missing or invalid")
    r.end_section()

    r.section("🚫 MCP Absence Check")
    manifests = [root / ".codex-plugin", root / ".claude-plugin", root / "plugin.json"]
    r.check(not _contains(manifests, "mcpServers"), "No MCP in plugin manifests", "MCP configuration found in plugin manifests!")
    r.check(not (root / ".mcp.json").exists(), "No .mcp.json file", ".mcp.json file exists — MCP is prohibited")
    config_mcp = any(_contains([root / "config"], n) for n in ("mcpServers", "mcp-configs", "mcp_server"))
    r.check(not config_mcp, "No MCP configuration in config/", "MCP references found in config/")
    r.end_section()

    r.section("📄 YAML Configuration")
    for name in ("config/routing.yaml", "config/priorities.yaml"):
        path = root / name
        r.check(path.is_file() and _yaml_ok(path), f"{name} valid YAML", f"{name} missing or invalid YAML")
    r.end_section()

    r.section("🗂️  Capability Registry")
    from ..registry import loader, schema
    try:
        problems = loader.structure_problems(root)
        cards = loader.load_cards(root)
    except (OSError, loader.RegistryError) as exc:
        problems, cards = [str(exc)], {}
    r.check(not problems and cards, f"capabilities/ layout consistent ({len(cards)} cards in {len(loader.load_domains(root)) if cards else 0} domains)",
            "capabilities/ layout inconsistent: " + "; ".join(problems[:3]))
    card_problems = schema.validate_cards(cards) if cards else ["no cards"]
    r.check(not card_problems, "All capability cards match the registry schema (spec §13)",
            "Capability card problems: " + "; ".join(card_problems[:3]))
    no_doc = [cid for cid in cards if not (loader.capabilities_dir(root) / cid / "CARD.md").is_file()]
    r.check(cards and not no_doc, "Every capability has an L1 CARD.md", f"CARD.md missing for {no_doc[:5]}")
    r.end_section()

    r.section("🎯 Skills")
    for skill_dir in sorted((root / "skills").glob("agylite-*/")):
        r.check((skill_dir / "SKILL.md").is_file(), f"{skill_dir.name}/SKILL.md exists", f"{skill_dir.name}/SKILL.md missing")
    r.end_section()

    r.section("🧠 Runtimes")
    from ..paths import current_bundle, agylite_home
    from ..runtimes import graphify
    h = graphify.health(agylite_home(), current_bundle())
    if h["status"] == "ready":
        r.ok(f"graphify {h.get('version') or ''} ready ({h['lock']})")
    else:   # MR-09: codebase work falls back to limited structural analysis (§74); not a failure
        r.warn(f"graphify {h['status']}: {h['reason']} — codebase analysis uses the structural fallback")
    r.end_section()

    r.section("📦 No Upstream Copies")
    r.check(not (root / "vendor").exists(), "No vendor/ directory", "vendor/ directory exists — upstream copies prohibited")
    r.ok("No upstream repository copies detected")
    r.end_section()

    r.section("🏷️  Version Consistency")
    version_file = root / "VERSION"
    if version_file.is_file():
        version = version_file.read_text(encoding="utf-8").strip()
        found = {name: (_json(root / name) or {}).get("version", "")
                 for name in ("plugin.json", ".codex-plugin/plugin.json", ".claude-plugin/plugin.json")}
        r.check(all(v == version for v in found.values()),
                f"Version consistent across VERSION, plugin.json, and host manifests: {version}",
                f"Version mismatch: VERSION={version}, " + ", ".join(f"{k}={v}" for k, v in found.items()))
    else:
        r.fail("VERSION file missing")
    r.end_section()

    from ..paths import current_bundle
    host_and_supply_checks(r, root, user_home, current_bundle())

    r.section("📝 Key Files")
    for name in KEY_FILES:
        r.check((root / name).is_file(), f"{name} exists", f"{name} missing")
    r.end_section()

    print("=======================================")
    print(f"Results: ✅ {r.passed} passed, ❌ {r.failed} failed, ⚠️  {r.warned} warnings")
    if r.failed:
        print("❌ Doctor found issues. Please fix the failures above.")
        return 1
    print("✅ All doctor checks passed!")
    return 0
