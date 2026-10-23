"""D-049 / IMPLEMENTATION_PLAN §4.1: the browser check FAILS the broken fixture site listing each planted defect and
PASSES the fixed one with three screenshots and a report.json whose hashes match; flows are plain data (scripts are
rejected); without the runtime, verify records the browser check as BLOCKED, never as passed."""
import hashlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.insert(0, ROOT_DIR)

from agylite.paths import agylite_home  # noqa: E402
from agylite.runtimes import browser  # noqa: E402
from agylite.verify import browser as verify_browser  # noqa: E402

FIX = Path(ROOT_DIR) / "tests" / "fixtures" / "browser"
READY = browser.health(agylite_home())["status"] == "ready"


class TestFlows(unittest.TestCase):
    def test_plain_steps_are_accepted(self):
        flows = browser.load_flows(FIX / "fixed-site" / ".agylite" / "flows.yaml")
        self.assertEqual(flows[0]["name"], "add to cart")
        self.assertEqual(len(flows[0]["steps"]), 3)

    def test_scripts_and_unknown_steps_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "flows.yaml"
            for bad in ("flows: [{name: x, steps: [{eval: 'document.cookie'}]}]",
                        "flows: [{name: x, steps: [{goto: /, click: {name: A}}]}]",
                        "flows: [{steps: [{goto: /}]}]"):
                p.write_text(bad, encoding="utf-8")
                with self.assertRaises(browser.BrowserError):
                    browser.load_flows(p)

    def test_defects_from_a_result(self):
        r = {"console_errors": [{"text": "boom"}], "failed_requests": [{"url": "/x.png", "status": 404}],
             "overflow": {"width": 390, "scrollWidth": 600, "clientWidth": 390}, "images_without_alt": ["x.png"],
             "flows": [{"ok": False, "error": "add step 3: expected text"}]}
        self.assertEqual(len(browser.defects(r)), 5)


class TestVerifyIntegration(unittest.TestCase):
    def test_ui_change_without_runtime_is_blocked(self):
        class P:
            root = Path("/tmp/project")
        with mock.patch.object(browser, "health", return_value={"status": "not-installed"}):
            chk = verify_browser.checks(P(), ["src/App.tsx"])
        self.assertEqual(len(chk), 1)
        self.assertIsNone(chk[0][1])
        self.assertIn("NOT_RUN", chk[0][0].notes[0])

    def test_backend_change_needs_no_browser(self):
        class P:
            root = Path("/tmp/project")
        self.assertEqual(verify_browser.checks(P(), ["api/orders.py"]), [])


@unittest.skipUnless(READY, "browser runtime not installed (`agylite runtime install browser`)")
class TestFixtureSites(unittest.TestCase):
    def test_broken_site_fails_with_each_planted_defect(self):
        with tempfile.TemporaryDirectory() as out:
            r = browser.check(FIX / "broken-site", agylite_home(), out=out)
        self.assertEqual(r["result"], "FAILED")
        text = "\n".join(r["defects"])
        for planted in ("undefinedFunction is not defined", "missing-lamp.png (404)", "horizontal overflow at 390 px",
                        "image without alt text", "flow failed"):
            self.assertIn(planted, text)

    def test_fixed_site_passes_with_hashed_evidence(self):
        with tempfile.TemporaryDirectory() as out:
            r = browser.check(FIX / "fixed-site", agylite_home(), out=out)
            self.assertEqual(r["result"], "PASSED", r["defects"])
            rep = json.loads((Path(out) / "report.json").read_text(encoding="utf-8"))
            shots = [a for a in rep["artifacts"] if a["path"].startswith("screenshot-")]
            self.assertEqual(sorted(a["path"] for a in shots),
                             ["screenshot-1440.png", "screenshot-390.png", "screenshot-768.png"])
            for a in rep["artifacts"]:
                self.assertEqual(hashlib.sha256((Path(out) / a["path"]).read_bytes()).hexdigest(), a["sha256"])


if __name__ == "__main__":
    unittest.main()
