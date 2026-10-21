"""MP1 F4: a request no capability fits says so (unmatched, principles only) and is recorded without its text."""
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
from agylite.events import read  # noqa: E402
from agylite.project.identity import detect  # noqa: E402
from agylite.routing import Router  # noqa: E402

NOBODY = "Translate my grandmother's recipe into Italian"


class TestUnmatched(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.router = Router()

    def test_unmatched_route(self):
        r = self.router.route(NOBODY)
        self.assertEqual((r["unmatched"], r["confidence"], r["capabilities"]), (True, "none", []))
        self.assertEqual(r["fallback_guidance"], ["engineering/principles"])

    def test_matched_route(self):
        r = self.router.route("Improve checkout security.")
        self.assertEqual((r["unmatched"], r["fallback_guidance"]), (False, []))


class TestUnmatchedCli(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        self.home = base / "home"
        self.root = make_project(base)
        self.env = mock.patch.dict(os.environ, {"AGYLITE_HOME": str(self.home)})
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.tmp.cleanup()

    def run_cli(self, *argv):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = main(list(argv))
        return code, out.getvalue()

    def test_brief_and_event(self):
        code, out = self.run_cli("route", NOBODY, "--brief", "--project", str(self.root))
        self.assertEqual(code, 0)
        self.assertIn("UNMATCHED · no capability fits; using principles only", out)
        events = read(detect(self.root, home=self.home), event="ROUTE_UNMATCHED")
        self.assertEqual(len(events), 1)
        details = events[0]["details"]
        self.assertIn("recipe", details["keywords"])
        self.assertEqual(details["length"], len(NOBODY))
        self.assertNotIn(NOBODY, json.dumps(events))

    def test_matched_route_records_no_unmatched_event(self):
        self.run_cli("route", "Improve checkout security.", "--brief", "--project", str(self.root))
        self.assertEqual(read(detect(self.root, home=self.home), event="ROUTE_UNMATCHED"), [])


if __name__ == "__main__":
    unittest.main()
