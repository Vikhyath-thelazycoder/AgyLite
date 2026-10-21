import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.insert(0, ROOT_DIR)

from agylite.bundle import checks  # noqa: E402
from agylite.bundle.transforms import gstack, rewrites  # noqa: E402

FM = "---\nname: demo\ndescription: Demo skill.\n---\n"
TMPL = FM + """
{{PREAMBLE}}

# Demo skill heading that is long enough to anchor

{{KEEP_ME}}

This literal paragraph is long enough to be a strong anchor.

{{SECTION:alpha}}

Closing literal paragraph that is also a strong anchor.
"""
GEN = FM + """<!-- AUTO-GENERATED -->
## Preamble (run first)
run gstack-skill-start and send telemetry

# Demo skill heading that is long enough to anchor

KEPT METHODOLOGY TEXT

This literal paragraph is long enough to be a strong anchor.

> generated pointer

Closing literal paragraph that is also a strong anchor.
"""


class TestGstackRenderer(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        root = Path(self._tmp.name)
        (root / "demo" / "sections").mkdir(parents=True)
        (root / "demo" / "SKILL.md.tmpl").write_text(TMPL, encoding="utf-8")
        (root / "demo" / "SKILL.md").write_text(GEN, encoding="utf-8")
        (root / "demo" / "sections" / "manifest.json").write_text(json.dumps({"sections": [
            {"id": "alpha", "file": "alpha.md", "title": "Alpha step", "trigger": "running step 2"}]}), encoding="utf-8")
        self.renderer = gstack.Renderer(root, None)

    def tearDown(self):
        self._tmp.cleanup()

    def test_keeps_methodology_drops_runtime_and_points_to_sections(self):
        out, unresolved = self.renderer.render("demo/SKILL.md.tmpl", TMPL)
        self.assertEqual(unresolved, [])
        self.assertIn("KEPT METHODOLOGY TEXT", out)
        self.assertNotIn("gstack-skill-start", out)
        self.assertNotIn("telemetry", out)
        self.assertIn("Read `sections/alpha.md` when running step 2.", out)
        self.assertNotIn("{{", out)
        self.assertTrue(out.startswith(FM))

    def test_unknown_placeholder_is_reported_not_guessed(self):
        tmpl = TMPL.replace("{{KEEP_ME}}", "{{NEVER_GENERATED}}")
        out, unresolved = self.renderer.render("other/SKILL.md.tmpl", tmpl)
        self.assertEqual(unresolved, ["NEVER_GENERATED"])
        self.assertIn("gstack placeholder NEVER_GENERATED not recovered", out)

    def test_weak_anchor_is_not_used(self):
        isolated, groups = gstack.align("{{A}}\n---\n{{B}}\n\nThis closing literal is long enough to anchor safely.\n",
                                        "a text\n---\nmore a\n---\nb text\n\nThis closing literal is long enough to anchor safely.\n")
        self.assertEqual(isolated, {})
        self.assertEqual(len(groups), 1)


# Minimal stand-in with every anchor the Appllama rewrites target (the real file is staged, not committed).
APPLLAMA_SAMPLE = """---
description: Build screens ... pairs with the Appllama MCP.
---

# Appllama App Design Skill

## The Prime Directive: study before you draw

1. If the **Appllama MCP** is connected, pull real screens.

## Navigation laws

6. **Study the grammar, not just the pixels.** Walking a winning flow on
   Appllama, note what each step *is* — push, modal, sheet — and copy that
   consistency.

## Anti-slop laws

1. No AI-default styling.

## Motion laws

- The bar: 60 fps through the hero flow, measured on a release build. Watch the recording once for feel, once frame
  by frame, and again next day with fresh eyes.

## State architecture

- Server state in TanStack Query.

## Perceived performance

- Cold-start TTI and bundle discipline live in
  [references/performance.md](references/performance.md) — apply the
  measure → optimize → re-measure loop, never blind memoization.

## Image & illustration assets

- Generate assets with the Higgsfield MCP/CLI if connected.

## The simulator loop (non-negotiable)

2. Screenshot (`xcrun simctl io booted screenshot s.png`) and actually look.

### The full-motion pass (mandatory, per flow)

Screen-record the entire flow.

## Definition of done, per screen

- [ ] Studied 10+ real reference screens via Appllama MCP

## References

| [references/simulator-loop.md](references/simulator-loop.md) | Final verification |
| [references/image-assets.md](references/image-assets.md) | Images |
"""


class TestRewrites(unittest.TestCase):
    def test_each_rewrite_applies(self):
        samples = {
            ("unlazy", "SKILL.md"): "Install:\nnode <skill-dir>/scripts/install-hooks.mjs\n",
            ("beyondseo", "SKILL.md"): ("For an installation request, follow [the host-specific guide](docs/agent-installation.md), "
                                        "including Cursor, Lovable workspace imports and agents managing Vercel projects. Rest.\n\n"
                                        "For Lovable execution, read [the Lovable host guide](docs/lovable.md) for details.\n\nNext."),
            ("ecc", "rules/README.md"): "```bash\n./install.sh typescript\n./install.sh python\n```\n",
            ("uiuxpromax", ".claude/skills/ui-ux-pro-max/SKILL.md"): 'python "${CLAUDE_PLUGIN_ROOT}/.claude/skills/ui-ux-pro-max/scripts/search.py"',
            ("appllama", "skills/appllama-app-design-skill/SKILL.md"): APPLLAMA_SAMPLE,
            ("gstack", "review/SKILL.md"): ("From the installed /review SKILL.md's directory, choose one path:\n"
                                            "- If the caller directory is `review`, Read `../qa/sections/exploratory.md` in full.\n"
                                            "Resolve QA's `sections/...` and `templates/...` paths from that installed QA "
                                            "SKILL.md directory, not the caller or product directory.\n"),
        }
        staged = os.path.join(ROOT_DIR, ".staging", "upstream")
        for key in (("addy", "agents/web-performance-auditor.md"),
                    ("graphify", "graphify/skills/claude/references/exports.md")):   # P13 rewrites: real upstream text
            path = os.path.join(staged, key[0], key[1])
            if os.path.isfile(path):
                with open(path, encoding="utf-8") as f:
                    samples[key] = f.read()
        if not os.path.isdir(staged):
            self.skipTest("staged upstreams needed for the P13 rewrite samples")
        for key in POCOCK_ADAPT:                                    # MP3 §1.3: real upstream text
            with open(os.path.join(staged, "pocock", key[1]), encoding="utf-8") as f:
                samples[key] = f.read()
        self.assertEqual(set(samples), set(rewrites.REWRITES))
        for (repo, path), text in samples.items():
            out = rewrites.apply(repo, path, text)
            self.assertNotEqual(out, text)
            self.assertNotIn("install-hooks.mjs", out)
            self.assertNotIn("docs/lovable.md", out)
            self.assertNotIn("./install.sh", out)
            self.assertNotIn("CLAUDE_PLUGIN_ROOT", out)
            for gone in ("Appllama MCP", "simctl", "Higgsfield", "references/performance.md", "sections/exploratory.md",
                         "references/simulator-loop.md", "references/image-assets.md"):
                self.assertNotIn(gone, out)

    def test_appllama_keeps_native_rules_and_local_verification(self):
        out = rewrites.apply("appllama", "skills/appllama-app-design-skill/SKILL.md", APPLLAMA_SAMPLE)
        self.assertIn("## Navigation laws", out)
        self.assertIn("## Verification (Agylite local test-first, D-035)", out)
        self.assertIn("design/visual-quality", out)  # anti-slop canonical in Taste/OpenDesign

    def test_drift_raises(self):
        with self.assertRaises(rewrites.RewriteDrift):
            rewrites.apply("unlazy", "SKILL.md", "upstream rewrote this section")


POCOCK_ADAPT = [("pocock", f"skills/{p}/SKILL.md") for p in (
    "productivity/grill-me", "engineering/grill-with-docs", "engineering/to-spec", "engineering/to-tickets",
    "engineering/wayfinder", "engineering/improve-codebase-architecture", "engineering/implement",
    "engineering/implement-spec", "engineering/tdd", "engineering/code-review", "productivity/handoff")]


@unittest.skipUnless(os.path.isdir(os.path.join(ROOT_DIR, ".staging", "upstream", "pocock")), "pocock not staged")
class TestPocockRewrites(unittest.TestCase):
    """MP3 §1.3: only mechanics change (tracker → plan, Skill tool → agylite skill load, frontmatter); the method
    text stays whole."""

    def adapted(self, key):
        with open(os.path.join(ROOT_DIR, ".staging", "upstream", *key), encoding="utf-8") as f:
            text = f.read()
        return text, rewrites.apply(*key, text)

    def test_no_host_mechanics_survive(self):
        for key in POCOCK_ADAPT:
            with self.subTest(key[1]):
                text, out = self.adapted(key)
                for gone in ("Skill tool", "/setup-matt-pocock-skills", "disable-model-invocation"):
                    self.assertNotIn(gone, out)
                self.assertIn("agylite", out)
                self.assertGreaterEqual(len(out), 0.9 * len(text) if len(text) > 1000 else 0)   # not shortened

    def test_skill_calls_load_the_bundled_skill(self):
        self.assertIn("Run `agylite skill load pocock/grilling`.", self.adapted(POCOCK_ADAPT[0])[1])
        out = self.adapted(("pocock", "skills/engineering/wayfinder/SKILL.md"))[1]
        self.assertIn("`agylite skill load pocock/grilling` and `agylite skill load pocock/domain-modeling`", out)
        self.assertIn("`agylite skills get pocock/research`", out)          # not bundled until MP5

    def test_tracker_is_the_plan(self):
        spec = self.adapted(("pocock", "skills/engineering/to-spec/SKILL.md"))[1]
        self.assertIn("In Agylite the tracker is the project's living plan. Write the spec to `docs/specs/<slug>.md`",
                      spec)
        self.assertIn("then save it as above; no labels.", spec)
        self.assertIn("## User Stories", spec)                              # the template is untouched
        tickets = self.adapted(("pocock", "skills/engineering/to-tickets/SKILL.md"))[1]
        self.assertIn("### 5. Publish the tickets to the plan", tickets)
        self.assertIn("--depends <task-id>", tickets)
        way = self.adapted(("pocock", "skills/engineering/wayfinder/SKILL.md"))[1]
        self.assertIn("## Wayfinder map: <destination>", way)
        self.assertIn("[grilling] Decide the auth model", way)


class TestChecks(unittest.TestCase):
    def test_hard_mcp_config(self):
        self.assertTrue(checks.hard_violations("x", "a/.mcp.json", "files/x/a/.mcp.json", b"{}"))
        self.assertTrue(checks.hard_violations("x", "c.yaml", "files/x/c.yaml", b"mcpServers:\n  a: {}"))
        self.assertFalse(checks.hard_violations("x", "doc.md", "files/x/doc.md", b"mcpServers mentioned in prose"))
        self.assertFalse(checks.hard_violations("graphify", "tests/fixtures/sample.mcp.json",
                                                "files/graphify/tests/fixtures/sample.mcp.json", b'{"mcpServers": {}}'))

    def test_soft_debts_only_for_adapt(self):
        self.assertEqual(checks.soft_debts("f.md", "ADAPT", b"call mcp__chrome__click"), [("mcp_mentions", "f.md")])
        self.assertEqual(checks.soft_debts("f.md", "PRESERVE", b"call mcp__chrome__click"), [])


if __name__ == "__main__":
    unittest.main()
