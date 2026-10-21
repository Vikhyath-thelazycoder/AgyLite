"""MP1 F5 part B: every entry skill that loads context passes the request, so sections are ranked for the task."""
import os
import unittest
from pathlib import Path

ROOT = Path(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))


class TestEntrySkillsPassTheRequest(unittest.TestCase):
    def test_context_calls_name_request_or_route(self):
        skills = sorted(ROOT.glob("skills/agylite-*/SKILL.md"))
        self.assertTrue(skills)
        for path in skills:
            text = path.read_text(encoding="utf-8")
            if "agylite context" in text:
                with self.subTest(path.parent.name):
                    self.assertTrue("--request" in text or "--route" in text, path)


if __name__ == "__main__":
    unittest.main()
