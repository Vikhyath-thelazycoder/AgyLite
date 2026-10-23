"""P27: one project through the whole OS with the network disabled — init → bootstrap → route → context →
codebase affected → verify → plan VERIFIED with evidence → Agent Office states → events — and no connection leaves
the machine (spec §45 offline, §91 integration)."""
import contextlib
import io
import json
import os
import socket
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.insert(0, ROOT_DIR)

from tests.context.fixtures import make_bundle, make_project  # noqa: E402
from agylite.cli import main  # noqa: E402
from agylite.dashboard.api import Office  # noqa: E402
from agylite.events import read  # noqa: E402
from agylite.project.identity import detect  # noqa: E402

PLAN = """# Implementation plan

## P1 · Payments
Status: IN_PROGRESS
"""
SRC = {"app/__init__.py": "", "app/payments.py": "def charge(e):\n    return 'ok'\n",
       "app/webhook.py": "from app.payments import charge\n\ndef handle(e):\n    return charge(e)\n",
       "tests/__init__.py": "",
       "tests/test_webhook_signature.py": "import unittest\nfrom app.webhook import handle\n\n"
                                          "class T(unittest.TestCase):\n    def test_ok(self):\n"
                                          "        self.assertEqual(handle({}), 'ok')\n"}

_real_connect = socket.socket.connect


def _guarded_connect(self, address):
    host = address[0] if isinstance(address, tuple) else address
    if isinstance(host, str) and (host.startswith("127.") or host in ("localhost", "::1")) or not isinstance(address, tuple):
        return _real_connect(self, address)
    raise AssertionError(f"network connection attempted to {address} (the OS must work offline)")


def run(*argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = main(list(argv))
    return code, out.getvalue(), err.getvalue()


class TestEndToEndOffline(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        self.home = base / "home"
        make_bundle(self.home)
        self.root = make_project(base, name="shop")
        for rel, text in SRC.items():
            (self.root / rel).parent.mkdir(parents=True, exist_ok=True)
            (self.root / rel).write_text(text, encoding="utf-8")
        self.env = mock.patch.dict(os.environ, {"AGYLITE_HOME": str(self.home), "AGYLITE_SESSION_ID": "s-e2e"})
        self.env.start()
        self.net = mock.patch.object(socket.socket, "connect", _guarded_connect)
        self.net.start()

    def tearDown(self):
        self.net.stop()
        self.env.stop()
        self.tmp.cleanup()

    def test_whole_flow(self):
        p = ["--project", str(self.root)]
        self.assertEqual(run("project", "init", "--existing", "--docs", *p)[0], 0)
        (self.root / "docs" / "IMPLEMENTATION_PLAN.md").write_text(PLAN, encoding="utf-8")
        code, out, err = run("plan", "add-task", "P1", "Verify webhook signatures", "--acceptance",
                             "forged signatures rejected", *p)
        self.assertEqual(code, 0, err)
        self.assertIn("T-1.1", out)

        code, out, _ = run("bootstrap", "--host", "claude-code", *p)
        self.assertEqual(code, 0)
        self.assertIn("L0 bootstrap", out)

        code, out, _ = run("route", "Fix the payment webhook security.", "--paths", "app/webhook.py", *p)
        route = json.loads(out)
        caps = [c["id"] for c in route["capabilities"]]
        self.assertIn("engineering/security", caps)
        self.assertEqual(route["verification_mode"], "tests-and-browser")
        self.assertEqual(route["browser"], "not-needed")   # D-049: backend change, no UI
        self.assertEqual(route["lifecycle"][0]["step"], "UNDERSTAND")
        self.assertIn("agylite codebase affected", route["impact"]["command"])

        code, out, _ = run("context", "engineering/security", "--request", "webhook signature", "--json", *p)
        self.assertEqual(code, 0)
        self.assertTrue(json.loads(out)["levels"])

        code, out, _ = run("codebase", "affected", "--paths", "app/payments.py", "--json", *p)
        aff = json.loads(out)
        self.assertEqual(aff["method"], "structural")          # no Graphify runtime in this home: stated fallback
        self.assertIn("tests/test_webhook_signature.py", [t["file"] for t in aff["tests"]])

        code, out, err = run("verify", "--paths", "app/webhook.py", "--task", "T-1.1", "--json", *p)
        ev = json.loads(out)
        self.assertEqual((code, ev["result"]), (0, "PASSED"), err)
        evidence = ev["evidence"]
        self.assertTrue((self.root / evidence).is_file())

        r = run("plan", "set-status", "T-1.1", "IN_PROGRESS", *p)
        self.assertEqual(r[0], 0, r[2])
        self.assertEqual(run("plan", "set-status", "T-1.1", "READY_FOR_VERIFICATION", *p)[0], 0)
        self.assertEqual(run("plan", "set-status", "T-1.1", "VERIFIED", "--evidence", evidence, *p)[0], 0)
        plan = (self.root / "docs" / "IMPLEMENTATION_PLAN.md").read_text(encoding="utf-8")
        self.assertIn("| T-1.1 | Verify webhook signatures | VERIFIED |", plan)
        self.assertIn(f"(evidence: {evidence})", plan)

        project = detect(self.root, home=self.home)
        seats = {s["id"]: s for s in Office(project).agents()["seats"]}
        self.assertNotEqual(seats["browser"]["state"], "disabled")   # D-049: an ordinary seat now
        self.assertIn(seats["security"]["state"], ("working", "idle"))
        self.assertEqual(seats["qa"]["say"], "verify: PASSED")

        kinds = [e["event"] for e in read(project)]
        for k in ("SESSION_STARTED", "DOMAIN_SELECTED", "CAPABILITIES_SELECTED", "CONTEXT_LOADED",
                  "VERIFICATION_STARTED", "VERIFICATION_PASSED", "TASK_STARTED"):
            self.assertIn(k, kinds)
        state = (self.root / ".agylite" / "state.yaml").read_text(encoding="utf-8")
        self.assertIn("tests-and-browser", state)
        self.assertFalse((self.root / ".vikhyath").exists())
        host = json.loads((self.home / "hosts" / "claude-code.json").read_text(encoding="utf-8"))
        self.assertEqual(host["bootstraps"], 1)


if __name__ == "__main__":
    unittest.main()
