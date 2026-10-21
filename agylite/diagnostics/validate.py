"""`agylite validate`: Python port of scripts/validate (v1.0.1)."""
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

from . import Report
from .doctor import PORTABLE_SCHEMA, _json

SHA = re.compile(r"^[0-9a-f]{40}$")


def _load_yaml(path: Path):
    import yaml
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError):
        return None


# Smoke routes: (request, stage, must include, must not include). The full scenario suite is tests/routing.
ROUTING_SMOKE = (
    ("Fix the payment webhook security.", "existing", {"engineering/security", "testing/security"}, {"design/", "seo/", "media/"}),
    ("This landing page looks generic. Make it feel premium.", "existing", {"design/design-direction"}, {"seo/", "engineering/backend"}),
    ("Audit my website.", "unknown", {"seo/auditing"}, {"engineering/", "testing/browser-exception"}),
    ("Open the website and show me what it looks like.", "existing", {"testing/local-verification"},
     {"testing/browser-exception"}),
    ("Make a launch video plan for our product.", "existing", {"media/launch-video"}, {"engineering/"}),
    ("Refactor the billing module", "existing", {"engineering/implementation"}, {"engineering/simplicity"}),
)


def _routing_problems(root: Path):
    from ..routing import ProjectFacts, Router, capability_ids
    from ..routing.rules import validate_routing
    router = Router(root)
    problems = validate_routing(router.cfg, router.cards, router.hierarchy)
    for request, stage, must, never in ROUTING_SMOKE:
        ids = capability_ids(router.route(request, project=ProjectFacts(stage=stage)))
        if not must <= set(ids) or any(i.startswith(n) for i in ids for n in never):
            problems.append(f"{request!r} routed to {ids}")
    return problems


# Files that must never be planned into a bundle (D-034 Appllama exclusions, D-035 browser verification).
FORBIDDEN_BUNDLE_PATHS = ("appllama:skills/appllama-usage/", "appllama:.mcp.json", "appllama:mcp.json",
                          "appllama:skills/appllama-app-design-skill/references/simulator-loop.md",
                          "addy:skills/browser-testing-with-devtools/", "ecc:skills/browser-qa/", "ecc:agents/e2e-runner.md",
                          "gstack:qa/sections/browser-", "gstack:design-review/")


def _forbidden_bundled(root: Path):
    from ..registry import generate
    planned = {f"{e['repo']}:{e['source_path']}" for e in generate.entries_from_plan()}
    return sorted(p for p in planned if p.startswith(FORBIDDEN_BUNDLE_PATHS))


def _pins(root: Path):
    data = _load_yaml(root / "docs/audit/evidence/upstream-staging-snapshot.yaml") or {}
    return {name: meta for name, meta in (data.get("snapshots") or {}).items()}


def _online(pins, r):
    failures = 0
    for meta in pins.values():
        url = f"https://api.github.com/repos/{meta['repo']}/commits/{meta['head']}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Agylite-OS-Validator"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                ok = resp.status == 200
        except OSError as exc:
            ok = False
            print(f"  ❌ {meta['repo']} @ {meta['head'][:8]} online check failed: {exc}")
        if ok:
            print(f"  ✅ {meta['repo']} @ {meta['head'][:8]} verified online")
        failures += not ok
    if failures:
        r.warn("Online verification failed or rate-limited. Offline structural tests remain valid.")
    else:
        r.ok(f"All {len(pins)} upstream pins verified against remote GitHub repositories")


def run(root: Path, online=False, unittests=True) -> int:
    r = Report("🧪 Agylite — Validation Suite")
    print("🌐 Mode: ONLINE (verifying remote GitHub commit SHAs)" if online
          else "📦 Mode: OFFLINE (structural and cryptographic format validation)")
    print()

    r.section("📦 Portable Manifest Tests")
    root_manifest = _json(root / "plugin.json") or {}
    r.check(root_manifest.get("$schema") == PORTABLE_SCHEMA and root_manifest.get("name") == "agylite"
            and "version" in root_manifest and "mcpServers" not in root_manifest and "skills" not in root_manifest,
            "Root plugin.json adheres to Agent Plugins 1.0.0 specification", "Root plugin.json failed specification validation")
    r.end_section()

    r.section("📋 Host Manifest Tests")
    codex = _json(root / ".codex-plugin/plugin.json") or {}
    r.check(codex.get("name") == "agylite" and "version" in codex and "skills" in codex
            and "mcpServers" not in codex, "Codex manifest valid, no MCP", "Codex manifest validation failed")
    claude = _json(root / ".claude-plugin/plugin.json") or {}
    r.check("name" in claude and "mcpServers" not in claude and "skills" not in claude,
            "Claude manifest valid minimal JSON, no MCP", "Claude manifest validation failed")
    m1, m2 = _json(root / ".agents/plugins/marketplace.json"), _json(root / ".claude-plugin/marketplace.json")
    try:
        markets_ok = m1["plugins"][0]["source"] == "./" and m2["plugins"][0]["source"] == "./"
    except (TypeError, KeyError, IndexError):
        markets_ok = False
    r.check(markets_ok, "Codex and Claude marketplace manifests valid", "Marketplace validation failed")
    r.check((root / ".agents/skills/agylite/SKILL.md").is_file(), "Antigravity skill adapter exists",
            "Antigravity skill adapter missing")
    r.end_section()

    r.section("🔀 Routing Tests")
    try:
        routing_problems = _routing_problems(root)
    except (OSError, KeyError, TypeError, ValueError) as exc:
        routing_problems = [f"{type(exc).__name__}: {exc}"]
    if not routing_problems:
        r.ok("Routing config v2 valid against the capability registry")
        for request, _, must, _ in ROUTING_SMOKE:
            r.ok(f"  {request} → {', '.join(sorted(must))}")
    else:
        r.fail("Routing validation failed: " + "; ".join(routing_problems[:3]))
    r.end_section()

    r.section("📦 Capability Registry Tests")
    from ..registry import generate, loader
    problems = generate.check(root)
    cards = loader.load_cards(root) if not problems else {}
    r.check(not problems, f"Registry valid: {len(cards)} capabilities, every spec §13 field generated, CARD.md current",
            "Capability registry validation failed: " + "; ".join(problems[:3]))
    testing = [c for c in cards if c.startswith("testing/")]
    r.check(cards and all(cards[c].get("web_qa_class") for c in testing),
            f"Web QA class recorded for all {len(testing)} testing capabilities (spec §23A.13)", "Web QA classes missing")
    simplicity = cards.get("engineering/simplicity", {})
    r.check(simplicity.get("activation_conditions", {}).get("mode") == "explicit"
            and simplicity.get("priority") == min((c["priority"] for c in cards.values()), default=0),
            "Simplicity review is explicit-only with the lowest priority", "Simplicity activation/priority invalid")
    r.end_section()

    r.section("🧪 Verification Policy (local test-first, D-035)")
    from ..verify import policy
    try:
        cfg = policy.load_policy(root)
        policy_problems = policy.policy_problems(cfg, cards)
    except (OSError, TypeError, ValueError) as exc:
        cfg, policy_problems = {}, [f"{type(exc).__name__}: {exc}"]
    r.check(not policy_problems, f"Verification mode {cfg.get('mode')}; design work adds Taste inspect (MP4); Chrome "
            "DevTools and visual browser QA disabled; no enabled capability needs a browser outside SEO/media/design",
            "Verification policy violated: " + "; ".join(policy_problems[:3]))
    r.check(not _forbidden_bundled(root), "No MCP config, appllama-usage, simulator loop or browser-QA file in the bundle plan",
            "Forbidden files in the bundle plan: " + ", ".join(_forbidden_bundled(root)[:3]))
    r.end_section()

    pins = _pins(root)
    if online:
        r.section("🌐 Online GitHub SHA Verification")
        _online(pins, r)
        r.end_section()

    r.section("🔒 Security Tests")
    manifest_text = "".join(p.read_text(encoding="utf-8", errors="ignore")
                            for p in [root / "plugin.json", *(root / ".codex-plugin").glob("*"), *(root / ".claude-plugin").glob("*")]
                            if p.is_file())
    r.check("mcpServers" not in manifest_text, "No MCP in manifests", "MCP found in manifests")
    r.check(not (root / ".mcp.json").exists(), "No .mcp.json", ".mcp.json exists")
    r.check(not (root / "vendor").exists(), "No vendor/ copies", "vendor/ directory exists")
    r.end_section()

    r.section("📌 Upstream Pins")
    licenses = _json(root / "third_party/licenses.json") or {}
    r.check(len(pins) > 0 and all(SHA.match(str(m.get("head", ""))) for m in pins.values()),
            f"All {len(pins)} upstreams pinned to 40-character hexadecimal SHAs", "Upstream pin missing or not a 40-hex SHA")
    r.check(sorted(pins) == sorted(licenses), "Every pinned upstream has a license record",
            "third_party/licenses.json does not match the pinned upstreams")
    r.end_section()

    if unittests:
        r.section("🧪 Unit Test Discovery")
        result = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", str(root / "tests"), "-p", "test_*.py"],
                                capture_output=True, text=True, cwd=root)
        r.check(result.returncode == 0, "All Python unit tests passed", "Python unit test discovery failed")
        r.end_section()

    print("=================================================")
    print(f"Results: ✅ {r.passed} passed, ❌ {r.failed} failed")
    if r.failed:
        print("❌ Validation failed. Fix the issues above.")
        return 1
    print("✅ All validation tests passed!")
    return 0
