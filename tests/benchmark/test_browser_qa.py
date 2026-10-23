"""browser-qa suite: the workspace hides the planted comments, and both scores are computed without a model."""
import os
import shutil
import sys
import unittest
from pathlib import Path

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.insert(0, ROOT_DIR)

from agylite.benchmark.quality.suites import browser_qa_runner as qa  # noqa: E402
from agylite.paths import agylite_home  # noqa: E402
from agylite.runtimes import browser  # noqa: E402

READY = browser.health(agylite_home())["status"] == "ready"
FIX = Path(ROOT_DIR) / "tests" / "fixtures" / "browser"


class TestBrowserQaSuite(unittest.TestCase):
    def test_workspace_keeps_the_defects_but_not_the_answers(self):
        ws = qa._workspace("t-browser-qa")
        try:
            html = (ws / "index.html").read_text(encoding="utf-8")
            self.assertNotIn("planted", html)
            self.assertIn("undefinedFunction();", html)
            self.assertIn('addEventListener("click", () => {});', html)
            self.assertFalse((ws / ".agylite").exists())
        finally:
            shutil.rmtree(ws)

    def test_reported_names_each_defect_once(self):
        text = ("1. ReferenceError: undefinedFunction is not defined on load\n2. missing-lamp.png returns 404\n"
                "3. The banner is 640px wide and scrolls horizontally on phones\n4. Add to cart button does nothing\n"
                "5. The image has no alt attribute\n")
        self.assertEqual(qa.reported(text), list(qa.DEFECTS))
        self.assertEqual(qa.reported("Everything looks fine."), [])

    @unittest.skipUnless(READY, "browser runtime not installed (`agylite runtime install browser`)")
    def test_remaining_sees_all_five_on_the_broken_site_and_none_when_fixed(self):
        broken = qa._workspace("t-browser-qa-broken")
        fixed = qa._workspace("t-browser-qa-fixed")
        try:
            for f in (FIX / "fixed-site").iterdir():
                if f.is_file():
                    shutil.copy2(f, fixed / f.name)
            self.assertEqual(qa.remaining(broken, agylite_home()), list(qa.DEFECTS))
            self.assertEqual(qa.remaining(fixed, agylite_home()), [])
        finally:
            shutil.rmtree(broken)
            shutil.rmtree(fixed)


if __name__ == "__main__":
    unittest.main()
