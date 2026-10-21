"""MP4 §3.3 (IMPLEMENTATION_PLAN §2.2): for a change that touches style or markup, `agylite verify` adds `agylite design
check`, Taste `lint` on the changed files and Taste `inspect` (0 FAIL) with its screenshots as hashed evidence. A missing
node>=22, browser or page is recorded as BLOCKED — never a silent pass. Backend changes get none of it."""
import hashlib
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.insert(0, ROOT_DIR)

from tests.context.fixtures import make_project  # noqa: E402
from agylite.project.identity import detect  # noqa: E402
from agylite.verify import design, engine, policy  # noqa: E402

READY = {"runtime": "taste", "status": "ready", "node": "node 22.14.0", "browser": "found /usr/bin/chromium"}


def by_name(selected):
    return {c.name: (cmd, c.notes) for c, cmd, _why, _t in selected}


class TestDesignVerify(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        self.env = mock.patch.dict(os.environ, {"AGYLITE_HOME": str(base / "home")})
        self.env.start()
        self.root = make_project(base)
        (self.root / "index.html").write_text("<h1>Tide tables</h1>\n", encoding="utf-8")
        (self.root / "styles.css").write_text("h1{color:#111}\n", encoding="utf-8")
        self.project = detect(self.root)

    def tearDown(self):
        self.env.stop()
        self.tmp.cleanup()

    def test_only_style_and_markup_changes_get_design_checks(self):
        self.assertEqual(design.design_files(["styles.css", "app/api.py", "src/Hero.tsx", "README.md"]),
                         ["styles.css", "src/Hero.tsx"])
        with mock.patch.object(design.taste, "health", return_value=READY):
            self.assertEqual(design.checks(self.project, ["app/api.py"]), [])
            names = by_name(design.checks(self.project, ["styles.css"]))
        self.assertEqual(set(names), {"design tokens", "taste lint", "taste inspect"})
        lint, _ = names["taste lint"]
        self.assertEqual(lint[lint.index("lint"):], ["lint", "styles.css"])     # the changed files only
        inspect, _ = names["taste inspect"]
        self.assertEqual(inspect[-1], str(Path(self.project.root) / "index.html"))   # default: the project's index.html

    def test_missing_node_browser_or_page_is_blocked_not_passed(self):
        broken = {**READY, "status": "broken", "node": "missing: node>=22", "browser": "missing"}
        with mock.patch.object(design.taste, "health", return_value=broken):
            names = by_name(design.checks(self.project, ["styles.css"]))
        self.assertEqual(names["taste lint"], (None, ["NOT_RUN: taste lint (node>=22 missing)"]))
        self.assertIsNone(names["taste inspect"][0])
        (self.root / "index.html").unlink()
        with mock.patch.object(design.taste, "health", return_value=READY):
            names = by_name(design.checks(self.project, ["styles.css"]))
        self.assertEqual(names["taste inspect"][1], ["NOT_RUN: taste inspect (no page: pass --inspect <url or file>)"])
        with mock.patch.object(design.taste, "health", return_value={**READY, "browser": "missing"}), \
                mock.patch.object(engine.detect, "detect", return_value=[]):
            record, _rel, results = engine.verify(self.project, ["styles.css"], inspect="https://example.com")
        insp = next(r for r in results if r["name"] == "taste inspect")
        self.assertEqual((insp["result"], insp["diagnosis"]), ("BLOCKED", ["NOT_RUN: browser (chrome missing)"]))
        self.assertNotEqual(record["result"], "PASSED")

    def test_inspect_fails_on_any_fail_and_records_hashed_screenshots(self):
        shots = self.root / ".taste-skill" / "inspect"
        shots.mkdir(parents=True)
        (shots / "desktop-1440.png").write_bytes(b"png-bytes")

        def fake(cmd, cwd, timeout=None):
            out = "RESULT: 2 FAIL, 1 WARN" if cmd[-2] == "inspect" or "inspect" in cmd else "ok"
            code = 1 if "inspect" in cmd else 0
            return {"command": cmd, "exit_code": code, "result": "FAILED" if code else "PASSED", "duration_ms": 1,
                    "diagnosis": [], "output_tail": out}
        with mock.patch.object(design.taste, "health", return_value=READY), \
                mock.patch.object(engine.detect, "detect", return_value=[]), \
                mock.patch.object(engine.run, "run_check", side_effect=fake):
            record, _rel, results = engine.verify(self.project, ["styles.css"])
        insp = next(r for r in results if r["name"] == "taste inspect")
        self.assertEqual((insp["result"], insp["fails"], insp["warns"]), ("FAILED", 2, 1))
        self.assertEqual(insp["artifacts"], [{"path": ".taste-skill/inspect/desktop-1440.png",
                                              "sha256": hashlib.sha256(b"png-bytes").hexdigest()}])
        self.assertEqual(record["result"], "FAILED")

    def test_policy_allows_design_browser_checks_only(self):
        cfg = policy.load_policy()
        self.assertFalse(cfg["disabled"]["browser_visual_verification"])
        self.assertTrue(cfg["disabled"]["chrome_devtools"])                 # the rest waits for Phase 7
        self.assertIn("agylite design taste inspect", " ".join(cfg["design_verification"]["commands"]))


if __name__ == "__main__":
    unittest.main()
