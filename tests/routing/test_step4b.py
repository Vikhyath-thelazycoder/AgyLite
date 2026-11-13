"""Step 4b (doc 24, plan 4b.6): EGM agents, React gating, merged review and the host subagent flag."""
import json
import os
import re
import sys
import tempfile
import unittest
from pathlib import Path

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.insert(0, ROOT_DIR)

from agylite.bundle.transforms import rewrites  # noqa: E402
from agylite.context.prompt_hook import review_lines  # noqa: E402
from agylite.project.lifecycle import detect_stack  # noqa: E402
from agylite.routing import ProjectFacts, Router  # noqa: E402

EGM = Path(ROOT_DIR, ".staging", "upstream", "egm")
ASTRYX = Path(ROOT_DIR, ".staging", "upstream", "astryx")


class TestReactGate(unittest.TestCase):
    def stack(self, deps, shadcn=False):
        with tempfile.TemporaryDirectory() as d:
            Path(d, "package.json").write_text(json.dumps({"dependencies": deps}))
            if shadcn:
                Path(d, "components.json").write_text("{}")
            return detect_stack(Path(d))

    def test_stack_tags(self):
        self.assertIn("react19", self.stack({"react": "^19.1.0"}))
        self.assertNotIn("react19", self.stack({"react": "^18.3.1"}))
        self.assertIn("ui-kit", self.stack({"react": "^19.0.0", "@radix-ui/react-dialog": "1"}))
        self.assertIn("ui-kit", self.stack({"react": "^19.0.0"}, shadcn=True))
        self.assertNotIn("ui-kit", self.stack({"react": "^19.0.0", "zod": "3"}))

    def test_react_settings_page_routes_astryx_only_without_a_design_system(self):
        r = Router()
        ids = lambda stack: [c["id"] for c in r.route("Build a settings page for the React app",
                                                      project=ProjectFacts(stage="existing", stack=stack))["capabilities"]]
        self.assertIn("design/react-design-system", ids(("node", "react", "react19")))
        self.assertNotIn("design/react-design-system", ids(("node", "react", "react19", "ui-kit")))
        self.assertNotIn("design/react-design-system", ids(("node", "react")))

    def test_react_guide_forbids_the_global_mode(self):
        text = Path(ROOT_DIR, "capabilities", "design", "react-design-system", "GUIDE.md").read_text(encoding="utf-8")
        self.assertIn("Never the global mode", text)
        self.assertIn("install-once", text)


class TestMergedReview(unittest.TestCase):
    def route(self, text):
        return Router().route(text, project=ProjectFacts(stage="existing"))

    def test_several_reviewers_merge_and_resolve_one_reviewer_does_not(self):
        merged = self.route("Review this PR for security and architecture issues")["review_merge"]
        self.assertEqual(merged["reviewers"][0], "ponytail/ponytail-review")
        self.assertIn("agylite:security-reviewer", merged["reviewers"])
        self.assertEqual((merged["merge"], merged["resolve"]), ("agylite:egm-synthesizer", "egm/egm-resolve"))
        self.assertIsNone(self.route("review this change")["review_merge"])

    def test_host_flag_decides_the_review_lines(self):
        route = self.route("Review this PR for security and architecture issues")
        self.assertIn("`Agent`", " ".join(review_lines(route, "claude-code")))
        self.assertIn("no subagent tool", " ".join(review_lines(route, "cursor")))
        spec = self.route("Review this design doc before we implement it")
        self.assertIn("Stop:", " ".join(review_lines(spec, "cursor")))
        self.assertNotIn("Stop:", " ".join(review_lines(spec, "claude-code")))

    def test_spec_review_is_suggested_after_a_spec_never_on_a_bug_fix(self):
        self.assertEqual([s["capability"] for s in self.route("Turn this into a spec")["suggest"]],
                         ["engineering/spec-review"])
        self.assertEqual(self.route("Fix the off-by-one bug in pagination")["suggest"], [])


@unittest.skipUnless(EGM.is_dir(), "staged EGM needed")
class TestEgmAgents(unittest.TestCase):
    def test_repo_agents_match_the_pinned_upstream(self):
        from agylite.bundle.egm_agents import render
        from agylite.bundle.provenance import load_pins
        for rel, text in render(EGM, load_pins()["egm"]["head"]).items():
            with self.subTest(rel):
                self.assertEqual(Path(ROOT_DIR, rel).read_text(encoding="utf-8"), text,
                                 "run `python -m agylite.bundle.egm_agents`")
                self.assertNotIn("CLAUDE_PLUGIN_ROOT", text)

    def test_every_agent_named_by_the_review_skills_exists(self):
        skills = {p.name for p in (EGM / "skills").iterdir()}
        for name in ("egm-review", "egm-review-loop"):
            text = (EGM / "skills" / name / "SKILL.md").read_text(encoding="utf-8")
            for agent in sorted(set(re.findall(r"\begm-[a-z-]*[a-z]\b", text)) - skills):
                with self.subTest(skill=name, agent=agent):
                    self.assertTrue(Path(ROOT_DIR, "agents", f"{agent}.md").is_file(), agent)


@unittest.skipUnless(ASTRYX.is_dir(), "staged Astryx needed")
class TestAstryxRecords(unittest.TestCase):
    def test_internal_frontmatter_is_stripped(self):
        for record in rewrites.ASTRYX_RECORDS:
            path = f"docs/design/{record}.md"
            out = rewrites.apply("astryx", path, (ASTRYX / path).read_text(encoding="utf-8"))
            for field in ("owners:", "review_triggers:", "deciding_specs:"):
                self.assertNotIn(field, out, record)
            self.assertIn("meta/astryx, MIT", out)


if __name__ == "__main__":
    unittest.main()
