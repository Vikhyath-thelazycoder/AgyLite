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



class TestReviewSkill(unittest.TestCase):
    def test_review_follows_ponytail_review_then_gstack(self):
        """MP3 §2.3: reviews follow ponytail-review's structure; each finding has its four parts; the reviewer reads
        the code the change touches; gstack's checklists are second."""
        text = (ROOT / "skills" / "agylite-review" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("agylite skill load ponytail/ponytail-review", text)
        for part in ("what it is", "what goes wrong", "the fix", "what happens if skipped"):
            self.assertIn(part, text)
        self.assertIn("not just the diff", text)
        self.assertLess(text.index("ponytail-review"), text.index("gstack"))
        self.assertNotIn("Simplicity review (Ponytail-derived) only when the user asks", text)

if __name__ == "__main__":
    unittest.main()
