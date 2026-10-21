"""MP4 §2.3 step 6: `design_check_overrides` in DESIGN.md front matter raise `agylite design check` limits (never lower
them), and the first check that uses them records a design decision; later checks do not record it again."""
import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.insert(0, ROOT_DIR)

from tests.context.fixtures import make_project  # noqa: E402
from agylite.cli import main  # noqa: E402
from agylite.design import tokens  # noqa: E402
from agylite.project import decisions  # noqa: E402
from agylite.project.identity import detect  # noqa: E402

CSS = "".join(f".c{i}{{border-radius:{r}px;color:#111111}}\n" for i, r in enumerate((2, 4, 8, 12, 16)))
DESIGN = "---\nmode: inspiration\ndesign_check_overrides:\n  radius_values: 5\n  font_families: 1\n---\n\n# Overview\n"


class TestOverrides(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        self.env = mock.patch.dict(os.environ, {"AGYLITE_HOME": str(base / "home")})
        self.env.start()
        self.root = make_project(base)
        (self.root / "app.css").write_text(CSS, encoding="utf-8")

    def tearDown(self):
        self.env.stop()
        self.tmp.cleanup()

    def radii(self):
        return next(c for c in tokens.check(self.root)["checks"] if c["check"] == "corner radii")

    def test_override_raises_the_limit_only(self):
        self.assertEqual((self.radii()["limit"], self.radii()["status"]), (4, "WARN"))
        (self.root / "DESIGN.md").write_text(DESIGN, encoding="utf-8")
        self.assertEqual((self.radii()["limit"], self.radii()["status"]), (5, "PASS"))
        fonts = next(c for c in tokens.check(self.root)["checks"] if c["check"] == "font families")
        self.assertEqual(fonts["limit"], 3)                      # an override never lowers a limit
        self.assertEqual(tokens.check(self.root)["overrides"], {"radius_values": 5})

    def test_first_use_records_one_design_decision(self):
        (self.root / "DESIGN.md").write_text(DESIGN, encoding="utf-8")
        for _ in range(2):
            with contextlib.redirect_stdout(io.StringIO()):
                main(["design", "check", "--project", str(self.root)])
        rows = decisions.find(detect(self.root), kind="design", topic="design-check-overrides")
        self.assertEqual(len(rows), 1)
        self.assertIn("radius_values", rows[0]["decision"])


if __name__ == "__main__":
    unittest.main()
