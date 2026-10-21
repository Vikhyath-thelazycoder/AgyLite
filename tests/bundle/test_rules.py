import os
import sys
import unittest

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.insert(0, ROOT_DIR)

from agylite.bundle import rules  # noqa: E402


class TestGlob(unittest.TestCase):
    def test_double_star_slash_matches_root_and_nested(self):
        rx = rules.glob_to_regex("**/SKILL.md")
        self.assertTrue(rx.match("SKILL.md"))
        self.assertTrue(rx.match("a/b/SKILL.md"))
        self.assertFalse(rx.match("a/SKILL.md.tmpl"))

    def test_single_star_stays_in_segment(self):
        rx = rules.glob_to_regex("design/*.md")
        self.assertTrue(rx.match("design/ui.md"))
        self.assertFalse(rx.match("design/sub/ui.md"))

    def test_trailing_double_star(self):
        rx = rules.glob_to_regex("skills/x/**")
        self.assertTrue(rx.match("skills/x/SKILL.md"))
        self.assertTrue(rx.match("skills/x/references/a.md"))
        self.assertFalse(rx.match("skills/xy/SKILL.md"))


class TestClassification(unittest.TestCase):
    def setUp(self):
        self.doc = {"repos": {"demo": {
            "default": {"decision": "EXCLUDE", "reason": "OUT_OF_DOMAIN"},
            "rules": [
                {"paths": ["skills/keep/**"], "decision": "ADAPT", "capability": "engineering/planning", "reason": "x"},
                {"paths": ["skills/**"], "decision": "EXCLUDE", "reason": "HOST_PORT"},
            ]}}}
        self.caps = rules.load_capabilities()

    def test_first_match_wins_then_default(self):
        self.assertEqual(rules.compile_rules(self.doc, self.caps), [])
        repo = self.doc["repos"]["demo"]
        self.assertEqual(rules.classify(repo, "skills/keep/SKILL.md")["decision"], "ADAPT")
        self.assertEqual(rules.classify(repo, "skills/other/SKILL.md")["reason"], "HOST_PORT")
        self.assertEqual(rules.classify(repo, "README.md")["reason"], "OUT_OF_DOMAIN")

    def test_unknown_capability_and_decision_are_errors(self):
        self.doc["repos"]["demo"]["rules"].append({"paths": ["x"], "decision": "COPY", "capability": "nope/nope", "reason": "x"})
        self.doc["repos"]["demo"]["rules"].append({"paths": ["y"], "decision": "STEAL", "reason": "x"})
        errors = rules.compile_rules(self.doc, self.caps)
        self.assertTrue(any("nope/nope" in e for e in errors))
        self.assertTrue(any("STEAL" in e for e in errors))


class TestRealRules(unittest.TestCase):
    def test_repo_rules_valid_and_cover_all_inventories(self):
        doc = rules.load_rules()
        caps = rules.load_capabilities()
        self.assertEqual(rules.compile_rules(doc, caps), [])
        inventories = sorted(f[:-4] for f in os.listdir(rules.evidence_dir() / "upstream-file-hashes"))
        self.assertEqual(sorted(doc["repos"]), inventories)

    def test_removed_upstream_taste_content_is_superseded(self):
        """MP1 F6: Taste v2.1 removed or moved these skills; the owner chose v2.1 only."""
        doc = rules.load_rules()
        self.assertEqual(rules.compile_rules(doc, rules.load_capabilities()), [])
        taste = doc["repos"]["taste"]
        for path in ("skills/output-skill/SKILL.md", "skills/soft-skill/SKILL.md", "skills/brandkit/SKILL.md",
                     "skills/stitch-skill/SKILL.md", "skills/redesign-skill/SKILL.md",
                     "skills/imagegen-frontend-web/SKILL.md"):
            with self.subTest(path):
                rule = rules.classify(taste, path)
                self.assertEqual((rule["decision"], rule["reason"]), ("EXCLUDE", "SUPERSEDED"))


if __name__ == "__main__":
    unittest.main()
