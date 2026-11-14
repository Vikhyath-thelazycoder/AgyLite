"""Skill quality plan, Phase 0: the free check finds each kind of defect, and installs carry a skill's references."""
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.insert(0, ROOT_DIR)

from agylite.adapters import get  # noqa: E402
from agylite.cli import build_parser  # noqa: E402
from agylite.diagnostics import skill_quality as sq  # noqa: E402

GOOD = """---
name: agylite-demo
description: Demo output — use when a demo is asked for.
---

# Agylite Demo

## Use when · Not for
## Steps
1. `agylite route "<request>"`, then `agylite codebase query|explain "<q>"`. See `references/examples.md`.
## Output
## Quality bar
## When something fails
"""

BAD = """---
name: agylite-demo
description: Demo output.
---

# Agylite Demo

## Steps
1. `agylite frobnicate`, then `agylite codebase nonsense`. See `references/missing.md` and `config/nope.yaml`.

Follow MP3 §2.3 (D-049). No browser or screenshot
verification.
"""


class TestSkillQuality(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.skill = self.root / "skills" / "agylite-demo" / "SKILL.md"
        (self.skill.parent / "references").mkdir(parents=True)
        (self.skill.parent / "references" / "examples.md").write_text("x", encoding="utf-8")
        self.parser = build_parser()

    def tearDown(self):
        self.tmp.cleanup()

    def check(self, text, kind="skill"):
        self.skill.write_text(text, encoding="utf-8")
        return sq.file_problems(self.skill, self.root, kind, self.parser)

    def test_good_skill_has_no_problems(self):
        self.assertEqual(self.check(GOOD), [])

    def test_each_defect_is_found(self):
        found = "\n".join(self.check(BAD))
        for needle in ("description does not say when", "section missing: ## Use when", "section missing: ## Output",
                       "missing file references/missing.md", "missing file config/nope.yaml",
                       "internal reference `MP3`", "internal reference `§`", "internal reference `D-049`",
                       "forbids browser verification", "unknown command `agylite frobnicate`",
                       "unknown command `agylite codebase nonsense`"):
            self.assertIn(needle, found)

    def test_size_limit_and_policy_mode(self):
        self.assertTrue(any("over the" in p for p in self.check(GOOD + "x" * sq.MAX_SKILL_BYTES)))
        self.skill.write_text(BAD, encoding="utf-8")
        local_only = sq.file_problems(self.skill, self.root, "skill", self.parser, mode="tests-only")
        self.assertFalse(any("forbids browser" in p for p in local_only))

    def test_a_tool_that_uses_no_browser_is_not_a_contradiction(self):
        text = GOOD + "\nRead-only: no browser or logged-in session is used.\n"
        self.assertEqual(self.check(text), [])

    def test_agent_needs_its_sections_and_the_incomplete_review_rule(self):
        found = "\n".join(self.check(GOOD, kind="agent"))
        self.assertIn("section missing: ## Method", found)
        self.assertIn("incomplete review", found)

    def test_repo_names_only_real_commands_and_files_resolve(self):
        """Holds today and must keep holding through the rewrite; the other kinds are the Phase 0 baseline."""
        found = sq.problems(Path(ROOT_DIR))
        self.assertEqual([p for p in found if "unknown command" in p], [])
        if sq.STRICT:
            self.assertEqual(found, [])


class TestInstallCarriesReferences(unittest.TestCase):
    def test_references_are_copied_and_stale_ones_removed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, user = Path(tmp) / "repo", Path(tmp) / "user"
            src = root / "skills" / "agylite-demo"
            (src / "references").mkdir(parents=True)
            src.joinpath("SKILL.md").write_text(GOOD, encoding="utf-8")
            (src / "references" / "examples.md").write_text("good and weak", encoding="utf-8")
            user.mkdir()
            cursor = get("cursor", root=root, home=Path(tmp) / "home", user_home=user)
            cursor.install()
            dest = user / ".cursor" / "skills" / "agylite-demo" / "references"
            self.assertEqual((dest / "examples.md").read_text(encoding="utf-8"), "good and weak")
            (src / "references" / "examples.md").unlink()
            (src / "references").rmdir()
            cursor.install()
            self.assertFalse(dest.exists())


if __name__ == "__main__":
    unittest.main()
