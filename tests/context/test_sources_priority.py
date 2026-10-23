"""MP1 F5: a capability's sources_priority decides which file loads first, with and without a request."""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.insert(0, ROOT_DIR)

from agylite.context.levels import _rank_files  # noqa: E402
from agylite.registry.generate import skill_path_problems, sources_priority_problems  # noqa: E402
from agylite.registry.schema import validate_card  # noqa: E402
from agylite.registry import loader  # noqa: E402

ENTRIES = [{"path": f"files/{p}/SKILL.md", "kind": "skill", "name": p, "description": d, "tokens": 100}
           for p, d in (("addy/a", "webhook review checklist"), ("taste/b", "visual design"), ("unlazy/c", "completion"))]


class TestRanking(unittest.TestCase):
    def test_without_priority_order_is_alphabetical(self):
        self.assertEqual(_rank_files(ENTRIES, None)[0]["path"], "files/addy/a/SKILL.md")

    def test_priority_first_with_and_without_query(self):
        prio = ["files/unlazy/c/SKILL.md"]
        self.assertEqual(_rank_files(ENTRIES, None, prio)[0]["path"], "files/unlazy/c/SKILL.md")
        # The request matches addy/a best, yet the declared primary source still leads.
        self.assertEqual(_rank_files(ENTRIES, "webhook review", prio)[0]["path"], "files/unlazy/c/SKILL.md")
        self.assertEqual(_rank_files(ENTRIES, "webhook review", prio)[1]["path"], "files/addy/a/SKILL.md")

    def test_globs_and_order_within_priority(self):
        prio = ["files/taste/**", "files/unlazy/*/SKILL.md"]
        self.assertEqual([e["path"] for e in _rank_files(ENTRIES, None, prio)],
                         ["files/taste/b/SKILL.md", "files/unlazy/c/SKILL.md", "files/addy/a/SKILL.md"])


class TestValidation(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.bundle = Path(self.tmp.name)
        files = {e["path"]: {"capability": "engineering/completion"} for e in ENTRIES}
        (self.bundle / "index.json").write_text(json.dumps({"files": files}), encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def test_overlap_and_rule_skill_paths_must_be_bundled(self):
        """D-050: the real skill_overlaps and rule `skill` paths are checked against the bundle index."""
        problems = skill_path_problems(self.bundle)
        self.assertTrue(any(p.startswith("skill_overlaps: files/pocock/skills/engineering/tdd/SKILL.md") for p in problems))
        self.assertTrue(any(p.startswith("rule to-tickets skill: ") for p in problems))
        from agylite.context.levels import skill_overlaps
        from agylite.routing.rules import load_routing
        files = {p: {} for pair in skill_overlaps() for p in pair}
        files.update({r["skill"]: {} for r in load_routing()["rules"] if r.get("skill")})
        (self.bundle / "index.json").write_text(json.dumps({"files": files}), encoding="utf-8")
        self.assertEqual(skill_path_problems(self.bundle), [])

    def test_glob_matching_nothing_fails(self):
        cards = {"engineering/completion": {"sources_priority": ["files/unlazy/c/SKILL.md", "files/gone/SKILL.md"]}}
        problems = sources_priority_problems(cards, self.bundle)
        self.assertEqual(len(problems), 1)
        self.assertIn("files/gone/SKILL.md", problems[0])

    def test_glob_must_match_a_file_of_the_same_capability(self):
        cards = {"design/visual-quality": {"sources_priority": ["files/taste/*/SKILL.md"]}}
        self.assertEqual(len(sources_priority_problems(cards, self.bundle)), 1)

    def test_exact_path_may_name_another_capabilitys_file(self):
        """MP4 §1.5: Taste's SKILL.md leads design/visual-quality and design/design-direction, but a file is bundled
        under one capability; an exact bundle path (no wildcard) may name another capability's file."""
        cards = {"design/visual-quality": {"sources_priority": ["files/taste/b/SKILL.md"]}}
        self.assertEqual(sources_priority_problems(cards, self.bundle), [])
        cards = {"design/visual-quality": {"sources_priority": ["files/taste/nope/SKILL.md"]}}
        self.assertEqual(len(sources_priority_problems(cards, self.bundle)), 1)

    def test_schema_rejects_non_bundle_paths(self):
        cards = loader.load_cards()
        card = dict(cards["engineering/completion"], sources_priority=["unlazy/SKILL.md"])
        self.assertTrue(any("sources_priority" in p for p in validate_card("engineering/completion", card, set(cards))))
        card["sources_priority"] = ["files/unlazy/SKILL.md"]
        self.assertFalse(any("sources_priority" in p for p in validate_card("engineering/completion", card, set(cards))))


if __name__ == "__main__":
    unittest.main()
