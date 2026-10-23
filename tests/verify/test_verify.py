"""P15 acceptance (D-035): a payment-webhook change selects its unit/signature/integration/idempotency/security tests
plus static checks; checks run locally with recorded counts; no browser process on any path; evidence is
machine-readable and recorded in project state; a browser exception only records."""
import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.insert(0, ROOT_DIR)

from tests.context.fixtures import make_project  # noqa: E402
from agylite.cli import main  # noqa: E402
from agylite.project import state as pstate  # noqa: E402
from agylite.project.identity import detect as detect_project  # noqa: E402
from agylite.verify import detect, engine, evidence, run, select  # noqa: E402

TEST = "import unittest\nfrom app.webhook import handle\n\nclass T(unittest.TestCase):\n    def test_it(self):\n        self.assertEqual(handle({}), {X})\n"
FILES = {
    "app/__init__.py": "", "app/payments.py": "def charge(e):\n    return 'ok'\n",
    "app/webhook.py": "from app.payments import charge\n\ndef handle(e):\n    return charge(e)\n",
    "app/reports.py": "def total():\n    return 1\n",
    "tests/__init__.py": "",
    "tests/test_webhook.py": TEST.replace("{X}", "'ok'"),
    "tests/test_webhook_signature.py": TEST.replace("{X}", "'ok'"),
    "tests/test_webhook_idempotency.py": TEST.replace("{X}", "'ok'"),
    "tests/integration/__init__.py": "", "tests/integration/test_payment_flow.py": TEST.replace("{X}", "'ok'"),
    "tests/security/__init__.py": "", "tests/security/test_webhook_auth.py": TEST.replace("{X}", "'ok'"),
    "tests/test_reports.py": "import unittest\nfrom app.reports import total\n\nclass R(unittest.TestCase):\n"
                             "    def test_total(self):\n        self.assertEqual(total(), 1)\n",
}


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        self.home = base / "home"
        self.root = make_project(base)
        for rel, text in FILES.items():
            (self.root / rel).parent.mkdir(parents=True, exist_ok=True)
            (self.root / rel).write_text(text, encoding="utf-8")
        self.project = detect_project(self.root, home=self.home)
        self.env = mock.patch.dict(os.environ, {"AGYLITE_HOME": str(self.home)})
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.tmp.cleanup()


class TestSelection(Base):
    def test_webhook_change_selects_its_tests_and_static_checks(self):
        impact, selected = engine.plan_for(self.project, ["app/webhook.py"])
        plan = engine.describe(selected, impact)
        test = next(c for c in plan["checks"] if c["kind"] == "test")
        kinds = {t["file"]: t["kind"] for t in test["tests"]}
        self.assertEqual(set(kinds), {"tests/test_webhook.py", "tests/test_webhook_signature.py",
                                      "tests/test_webhook_idempotency.py", "tests/integration/test_payment_flow.py",
                                      "tests/security/test_webhook_auth.py"})
        self.assertNotIn("tests/test_reports.py", kinds)
        self.assertEqual(kinds["tests/test_webhook_signature.py"], "security")
        self.assertEqual(kinds["tests/test_webhook_idempotency.py"], "idempotency")
        self.assertEqual(kinds["tests/integration/test_payment_flow.py"], "integration")
        self.assertEqual(kinds["tests/test_webhook.py"], "api")
        self.assertIn("build", [c["kind"] for c in plan["checks"]])
        self.assertIn("tests.security.test_webhook_auth", test["command"])

    def test_full_suite_when_nothing_narrower(self):
        _impact, selected = engine.plan_for(self.project, ["README.md"])
        test = next(s for s in selected if s[0].kind == "test")
        self.assertIn("full suite", test[2])

    def test_node_detection_and_e2e_never_default(self):
        (self.root / "package.json").write_text(json.dumps({"scripts": {
            "test": "vitest run", "test:e2e": "playwright test", "lint": "eslint .", "typecheck": "tsc --noEmit",
            "build": "vite build"}}), encoding="utf-8")
        checks = detect.detect(self.root)
        kinds = {c.name: c.kind for c in checks if c.toolchain == "node"}
        self.assertEqual(kinds, {"test": "test", "test:e2e": "e2e", "lint": "lint", "typecheck": "typecheck",
                                 "build": "build"})
        names = [c.name for c, *_ in select.plan(checks, None)]
        self.assertNotIn("test:e2e", names)


class TestRun(Base):
    def test_run_records_counts_evidence_and_state(self):
        pstate.init_state(self.project, stage="existing") if hasattr(pstate, "init_state") else None
        calls = []
        real = subprocess.run

        def spy(cmd, *a, **kw):
            calls.append(cmd)
            return real(cmd, *a, **kw)

        with mock.patch("agylite.verify.run.subprocess.run", side_effect=spy):
            record, rel, results = engine.verify(self.project, ["app/webhook.py"], task="T-1.1")
        self.assertEqual(record["result"], "PASSED", results)
        test = next(r for r in results if r["kind"] == "test")
        self.assertEqual((test["passed"], test["failed"]), (5, 0))
        data = json.loads((self.root / rel).read_text(encoding="utf-8"))
        self.assertEqual(evidence.validate(data), [])
        self.assertTrue(all({"command", "exit_code", "result", "at"} <= set(c) for c in data["checks"]))
        joined = " ".join(" ".join(c) for c in calls).lower()
        for word in ("chrome", "playwright", "puppeteer", "screenshot", "browser"):
            self.assertNotIn(word, joined)

    def test_failure_is_diagnosed_and_rerun(self):
        (self.root / "app" / "payments.py").write_text("def charge(e):\n    return 'bad'\n", encoding="utf-8")
        record, _rel, results = engine.verify(self.project, ["app/payments.py"], kinds=["test"])
        self.assertEqual(record["result"], "FAILED")
        r = results[0]
        self.assertEqual(r["failed"], 5)
        self.assertEqual(r["rerun"]["result"], "FAILED")
        self.assertFalse(r["flaky"])
        self.assertTrue(any("AssertionError" in d or "FAIL" in d for d in r["diagnosis"]))

    def test_missing_tool_is_blocked(self):
        r = run.run_check(["definitely-not-a-tool-xyz"], self.root)
        self.assertEqual(r["result"], "BLOCKED")

    def test_browser_commands_are_ordinary_checks(self):
        r = run.run_check([sys.executable, "-c", "print('chrome-devtools screenshot ok')"], self.root)   # D-049
        self.assertEqual(r["result"], "PASSED")

    def test_evidence_rejects_visual_claims(self):
        bad = {"result": "PASSED", "checks": [{"command": ["manual"], "exit_code": 0, "result": "PASSED",
                                               "at": "x", "note": "looks correct in the screenshot"}]}
        self.assertTrue(evidence.validate(bad))


class TestCli(Base):
    def test_plan_and_browser_flag(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(main(["verify", "--plan", "--paths", "app/webhook.py", "--json",
                                   "--project", str(self.root)]), 0)
        self.assertIn("tests/test_webhook_signature.py", out.getvalue())
        out = io.StringIO()   # D-049: --browser adds the browser check (BLOCKED when the runtime is missing)
        from agylite.runtimes import browser
        with mock.patch.object(browser, "health", return_value={"status": "not-installed"}), \
                contextlib.redirect_stdout(out):
            self.assertEqual(main(["verify", "--plan", "--browser", "--paths", "app/webhook.py", "--json",
                                   "--project", str(self.root)]), 0)
        self.assertIn("browser check", out.getvalue())
        self.assertIn("NOT_RUN: browser runtime missing", out.getvalue())

    def test_verify_updates_state(self):
        main(["project", "init", "--existing", "--project", str(self.root)])
        with contextlib.redirect_stdout(io.StringIO()):
            code = main(["test", "--paths", "app/webhook.py", "--task", "T-1.1", "--project", str(self.root)])
        self.assertEqual(code, 0)
        last = pstate.load_state(self.project)["verification"]["last"]
        self.assertEqual((last["result"], last["task"]), ("PASSED", "T-1.1"))
        self.assertTrue(last["evidence"].startswith(".agylite/evidence/"))


if __name__ == "__main__":
    unittest.main()
