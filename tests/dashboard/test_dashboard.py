"""P23 (D-043): Agent Office layout covers every capability; events map to agent states exactly; the server is
loopback-only, read-only, refuses path escapes and stops when idle."""
import json
import os
import sys
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.insert(0, ROOT_DIR)

from tests.context.fixtures import make_project  # noqa: E402
from agylite.dashboard import agents as office  # noqa: E402
from agylite.dashboard.server import Dashboard  # noqa: E402
from agylite.project.identity import detect  # noqa: E402
from agylite.registry.loader import load_cards  # noqa: E402

NOW = datetime(2026, 10, 11, 12, 0, tzinfo=timezone.utc)


def ev(event, caps=(), minutes_ago=1, severity="info", **details):
    return {"event": event, "capabilities": list(caps), "details": details, "severity": severity,
            "ts": (NOW - timedelta(minutes=minutes_ago)).isoformat(timespec="milliseconds")}


class TestLayout(unittest.TestCase):
    def test_every_capability_has_exactly_one_seat(self):
        self.assertEqual(office.validate_layout(office.load_layout(), set(load_cards())), [])

    def test_validator_catches_mistakes(self):
        layout = office.load_layout()
        layout["seats"][1]["caps"].append("engineering/security")       # seated twice
        layout["seats"][2]["caps"] = []                                 # backend caps unseated
        problems = " | ".join(office.validate_layout(layout, set(load_cards())))
        self.assertIn("engineering/security seated twice", problems)
        self.assertIn("engineering/backend has no seat", problems)


class TestStates(unittest.TestCase):
    def setUp(self):
        self.layout = office.load_layout()
        self.sources = {"engineering/security": ["affaan-m/ECC", "msitarzewski/agency-agents"],
                        "testing/security": ["affaan-m/ECC"]}

    def states(self, events):
        return {s["id"]: s for s in office.derive(self.layout, events, self.sources, now=NOW)}

    def test_route_lights_selected_agents_and_waits_on_dependencies(self):
        s = self.states([
            ev("DOMAIN_SELECTED", change_type="SECURITY_CHANGE", domains=["engineering", "testing"], minutes_ago=3),
            ev("CAPABILITIES_SELECTED", ["engineering/security", "testing/security"],
               dependencies=["codebase/impact-analysis"], minutes_ago=3)])
        self.assertEqual(s["security"]["state"], "working")
        self.assertEqual(s["sectest"]["state"], "working")
        self.assertEqual(s["mapper"]["state"], "waiting")
        self.assertEqual(s["agency"]["state"], "working")      # Agency is a source of engineering/security
        self.assertIn("SECURITY_CHANGE", s["security"]["say"])
        self.assertEqual(s["backend"]["state"], "idle")
        self.assertIn("agency-agents", s["security"]["sources"])

    def test_verification_and_risk(self):
        s = self.states([ev("VERIFICATION_STARTED", checks=2, minutes_ago=2),
                         ev("VERIFICATION_FAILED", result="FAILED", failed=["unittest"]),
                         ev("RISK_DETECTED", severity="high", rule="curl-pipe-to-shell")])
        self.assertEqual((s["qa"]["state"], s["qa"]["say"]), ("blocked", "verify failed: unittest"))
        self.assertEqual(s["beacon"]["state"], "blocked")
        self.assertIn("curl-pipe-to-shell", s["beacon"]["say"])
        s = self.states([ev("VERIFICATION_PASSED", result="PASSED")])
        self.assertEqual((s["qa"]["state"], s["qa"]["say"]), ("idle", "verify: PASSED"))

    def test_tasks(self):
        s = self.states([ev("TASK_BLOCKED", item="T-2.1", reason="waiting on API keys")])
        self.assertEqual(s["planner"]["state"], "blocked")
        self.assertIn("T-2.1", s["planner"]["say"])

    def test_policy_states_and_idle_timeout(self):
        s = self.states([ev("CAPABILITIES_SELECTED", ["testing/browser-verification", "engineering/review"],
                            minutes_ago=30)])
        self.assertEqual(s["browser"]["state"], "idle")           # D-049: browser verification is a normal seat
        self.assertEqual(s["simple"]["state"], "off")
        self.assertEqual(s["reviewer"]["state"], "idle")          # 30 min old → back to idle
        s = self.states([ev("CAPABILITIES_SELECTED", ["engineering/simplicity"])])
        self.assertEqual(s["simple"]["state"], "working")         # asked for explicitly → wakes up

    def test_activity_newest_first_and_readable(self):
        items = office.activity([ev("VERIFICATION_STARTED", checks=2, minutes_ago=2),
                                 ev("VERIFICATION_PASSED", evidence=".agylite/evidence/x.json")])
        self.assertEqual(items[0]["event"], "VERIFICATION_PASSED")
        self.assertIn("PASSED", items[0]["text"])


class TestServer(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        self.env = mock.patch.dict(os.environ, {"AGYLITE_HOME": str(base / "home")})
        self.env.start()
        self.project = detect(make_project(base), home=base / "home")

    def tearDown(self):
        self.env.stop()
        self.tmp.cleanup()

    def get(self, d, path):
        with urllib.request.urlopen(d.url + path, timeout=10) as r:
            return r.status, r.headers.get("Content-Type"), r.read()

    def test_serves_loopback_read_only_and_sleeps_when_idle(self):
        d = Dashboard(self.project, demo=True, sleep_after=1.0)
        self.assertEqual(d.httpd.server_address[0], "127.0.0.1")
        t = threading.Thread(target=d.serve)
        t.start()
        try:
            code, ctype, body = self.get(d, "")
            self.assertEqual((code, ctype.split(";")[0]), (200, "text/html"))
            self.assertIn(b"Agent Office", body)
            agents = json.loads(self.get(d, "api/agents")[2])
            self.assertTrue(agents["demo"])
            self.assertEqual(len(agents["seats"]), len(office.load_layout()["seats"]))
            for path in ("api/activity", "api/state", "api/hosts", "office.js", "office.css"):
                self.assertEqual(self.get(d, path)[0], 200, path)
            with self.assertRaises(urllib.error.HTTPError) as cm:
                self.get(d, "..%2f..%2fconfig/dashboard.yaml")
            self.assertEqual(cm.exception.code, 404)
            cm.exception.close()
            req = urllib.request.Request(d.url + "api/agents", data=b"{}", method="POST")
            with self.assertRaises(urllib.error.HTTPError) as cm:
                urllib.request.urlopen(req, timeout=10)
            self.assertEqual(cm.exception.code, 405)
            cm.exception.close()
        finally:
            t.join(timeout=15)
        self.assertFalse(t.is_alive())
        self.assertEqual(d.reason, "idle")
        from agylite.events import read
        kinds = [e["event"] for e in read(self.project)]
        self.assertIn("DASHBOARD_STARTED", kinds)
        self.assertIn("DASHBOARD_SLEEPING", kinds)


if __name__ == "__main__":
    unittest.main()
