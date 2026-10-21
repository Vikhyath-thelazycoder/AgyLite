"""MP2 §6: the quality harness itself — scoring math, isolation check, dry run / spend control, suite schemas."""
import json
import os
import re
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.insert(0, ROOT_DIR)

from agylite.benchmark.quality import harness, scoring, suites, tier1  # noqa: E402
from agylite.benchmark.quality.suites.addy_style import parse_grading  # noqa: E402


class TestScoring(unittest.TestCase):
    def test_retained_and_thresholds(self):
        self.assertEqual(scoring.verdict(2, 3, 3)["verdict"], "same")
        self.assertEqual(scoring.verdict(2, 3, 2.8)["verdict"], "near")
        self.assertEqual(scoring.verdict(2, 3, 2.5)["verdict"], "regressed")
        self.assertEqual(scoring.verdict(2, 3, 1)["verdict"], "regressed")      # worse than no skill
        v = scoring.verdict(2, 3, 2.9)
        self.assertEqual((v["verdict"], v["retained"]), ("same", 0.9))      # exactly 0.90 is same, never rounded up

    def test_lower_is_better_flips_the_sign(self):
        v = scoring.verdict(208, 65, 198, lower_is_better=True)                 # the pilot's vibe-todo
        self.assertEqual((v["retained"], v["verdict"]), (0.07, "regressed"))
        self.assertEqual(scoring.verdict(208, 65, 70, lower_is_better=True)["verdict"], "same")

    def test_no_upstream_gain_and_noise(self):
        self.assertEqual(scoring.verdict(1, 1, 1)["verdict"], "same")
        self.assertEqual(scoring.verdict(1, 1, 0)["verdict"], "regressed")
        v = scoring.verdict([2, 4, 3], [3, 5, 2], [3, 3, 3])                   # gain 0.33, stdev ~1
        self.assertEqual(v["verdict"], "inconclusive")
        self.assertEqual(scoring.verdict(None, 1, 1)["verdict"], "missing")

    def test_suite_is_its_weakest_metric(self):
        self.assertEqual(scoring.suite_verdict({"a": {"verdict": "same"}, "b": {"verdict": "near"}}), "near")


def _init(plugins, skills=(), mcp=()):
    return json.dumps({"type": "system", "subtype": "init", "model": "m", "claude_code_version": "x",
                       "plugins": [{"name": p, "source": f"{p}@inline"} for p in plugins]
                       + [{"name": "cc-plugin-telemetry", "source": "cc-plugin-telemetry@builtin"}],
                       "skills": list(skills), "mcp_servers": [{"name": m} for m in mcp]})


class TestIsolation(unittest.TestCase):
    def test_accepts_the_expected_set(self):
        arm = harness.ArmSetup("agylite", plugins=("agylite",))
        info = harness.check_isolation([_init(["agylite"], ["agylite:agylite-routing", "debug"])], arm)
        self.assertEqual(info["plugins"], ["agylite"])
        harness.check_isolation([_init([], ["debug"])], harness.ArmSetup("baseline"))

    def test_rejects_an_extra_plugin_skill_or_mcp(self):
        base = harness.ArmSetup("baseline")
        with self.assertRaises(harness.IsolationError):
            harness.check_isolation([_init(["agylite"])], base)
        with self.assertRaises(harness.IsolationError):
            harness.check_isolation([_init([], ["agylite:agylite-routing"])], base)
        with self.assertRaises(harness.IsolationError):
            harness.check_isolation([_init([], mcp=["claude.ai Claude Docs"])], base)
        with self.assertRaises(harness.IsolationError):
            harness.check_isolation(["{}"], base)


class TestDryRunAndSpend(unittest.TestCase):
    def test_dry_run_plans_and_starts_nothing(self):
        lines = []
        with mock.patch("subprocess.run") as sp, mock.patch("subprocess.Popen") as po:
            out = tier1.run("eng-addy", runs=2, tasks=["test-driven-development#1", "test-driven-development#2"],
                            dry_run=True, log=lines.append)
        self.assertEqual(out["planned"], 12)                   # 2 tasks × 3 arms × 2 runs
        self.assertEqual((sp.call_count, po.call_count), (0, 0))
        self.assertEqual(sum(1 for x in lines if x.startswith("[dry-run]")), 12)

    def test_no_session_without_yes_spend_or_over_the_cap(self):
        with mock.patch("subprocess.run") as sp:
            with self.assertRaises(harness.SpendRefused):
                tier1.run("eng-addy", tasks=["test-driven-development#1"], log=lambda *_: None)
            with self.assertRaises(harness.SpendRefused):
                tier1.run("eng-addy", yes_spend=True, max_sessions=2, log=lambda *_: None)
        self.assertEqual(sp.call_count, 0)

    def test_arm_order_alternates_between_runs(self):
        _cfg, _mod, matrix = tier1.plan("eng-addy", runs=2, tasks=["test-driven-development#1"])
        self.assertEqual([m["arm"] for m in matrix], ["baseline", "upstream", "agylite", "agylite", "upstream", "baseline"])


class TestSuiteSchema(unittest.TestCase):
    def test_every_suite_has_credits_license_and_a_full_sha(self):
        self.assertTrue(suites.names())
        for name in suites.names():
            with self.subTest(name):
                cfg = suites.load_suite(name)
                self.assertEqual(cfg["name"], name)
                self.assertTrue(cfg.get("tasks") and cfg.get("metrics") and cfg.get("credits"))
                mod = suites.module(cfg)
                self.assertEqual(sorted(mod.METRICS), sorted(cfg["metrics"]))
                for c in cfg["credits"]:
                    self.assertIn(c["license"], ("MIT", "Apache-2.0"))
                    self.assertRegex(c["commit"], r"^[0-9a-f]{40}$")


class TestAddyGrading(unittest.TestCase):
    def test_parse_requires_a_verdict_with_evidence_per_expectation(self):
        good = {"expectations": [{"id": 1, "text": "a", "passed": True, "evidence": "ran npm test"},
                                 {"id": 2, "text": "b", "passed": False, "evidence": "no test"}]}
        self.assertEqual(parse_grading("```json\n" + json.dumps(good) + "\n```", 2)["passed"], 1)
        bad = json.loads(json.dumps(good))
        bad["expectations"][1]["evidence"] = " "
        self.assertIsNone(parse_grading(json.dumps(bad), 2))
        self.assertIsNone(parse_grading(json.dumps(good), 3))


if __name__ == "__main__":
    unittest.main()
