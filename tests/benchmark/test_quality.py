"""MP2 §6: the quality harness itself — scoring math, isolation check, dry run / spend control, suite schemas."""
import json
import os
import re
import sys
import tempfile
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


class _FakeSuite:
    """A three-cell suite whose second session hits the usage limit (no real session starts)."""
    METRICS = {"score": False}

    def __init__(self, limit_at=None):
        self.limit_at, self.calls = limit_at, []

    def cells(self, cfg):
        return [{"task": f"t#{i}"} for i in (1, 2)]

    def run_cell(self, cell, ctx):
        self.calls.append(ctx["label"])
        if ctx["label"] == self.limit_at:
            raise harness.UsageLimit("You've hit your session limit · resets 10:40pm")
        return {"label": ctx["label"], "arm": ctx["arm"], "cost": 0.1, "metrics": {"score": 1.0}}


class TestUsageLimit(unittest.TestCase):
    """MP2 spending rule: on a usage-limit or rate-limit reply the run stops and says where to resume; a limit
    message is never graded as an answer."""

    def test_detects_limit_replies_only(self):
        for text in ("You've hit your session limit · resets 10:40pm (Asia/Calcutta)", "You've hit your weekly limit",
                     "API Error: 429 rate_limit_error", "Claude usage limit reached. Your limit will reset at 5pm"):
            self.assertTrue(harness.is_usage_limit(text), text)
        spec = ("I wrote the spec at `rate-limit/docs/specs/rate-limit.md`.\n\n**Requirements:** over the limit the API "
                "answers 429 with a Retry-After header; the rate window resets every minute.")   # eng-pocock to-spec#2
        for text in ("I fixed the pagination bug; the rate limiter test passes.", "", None, spec,
                     "You've hit your session limit · resets 10:40pm. " + "x" * 400):
            self.assertFalse(harness.is_usage_limit(text), text)

    def test_run_session_raises_on_a_limit_reply(self):
        trace = "\n".join([json.dumps({"type": "system", "subtype": "init", "plugins": [], "skills": [],
                                        "mcp_servers": []}),
                           json.dumps({"type": "result", "result": "You've hit your session limit · resets 10:40pm",
                                       "total_cost_usd": 0, "num_turns": 1})])
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch("subprocess.run", return_value=mock.Mock(stdout=trace, returncode=1)):
            with self.assertRaises(harness.UsageLimit):
                harness.run_session("p", Path(tmp), harness.ArmSetup("baseline"))
        # a grader call is plain-text `claude -p`, not stream-json
        with mock.patch("subprocess.run", return_value=mock.Mock(stdout="You've hit your session limit · resets 10:40pm\n")):
            with self.assertRaises(harness.UsageLimit):
                harness.ask("grade this")

    def test_run_stops_at_the_first_limit_and_resumes_only_missing_cells(self):
        with tempfile.TemporaryDirectory() as tmp:
            fake = _FakeSuite(limit_at="t-2__baseline__0")
            with mock.patch.object(suites, "module", return_value=fake):
                rep = tier1.run("eng-addy", yes_spend=True, out_root=Path(tmp), log=lambda *_: None, ledger=False)
            self.assertIn("session limit", rep["stopped"])
            self.assertEqual(fake.calls, ["t-1__baseline__0", "t-1__upstream__0", "t-1__agylite__0",
                                          "t-2__baseline__0"])            # nothing after the limit
            self.assertEqual(rep["sessions"], 3)                             # the limit cell is not a result
            self.assertIn("--resume " + rep["run_dir"], rep["resume"])
            again = _FakeSuite()
            with mock.patch.object(suites, "module", return_value=again):
                rep2 = tier1.run("eng-addy", yes_spend=True, resume=Path(rep["run_dir"]), log=lambda *_: None,
                                 ledger=False)
            self.assertEqual(again.calls, ["t-2__baseline__0", "t-2__upstream__0", "t-2__agylite__0"])
            self.assertEqual((rep2["run_dir"], rep2["sessions"], rep2.get("stopped")), (rep["run_dir"], 6, None))

    def test_resume_redoes_old_limit_replies_recorded_as_results(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp) / "r"
            run_dir.mkdir()
            old = [{"label": "t-1__baseline__0", "arm": "baseline", "task": "t#1", "run": 0, "metrics": {"score": 1.0}},
                   {"label": "t-1__upstream__0", "arm": "upstream", "task": "t#1", "run": 0, "metrics": {"score": None},
                    "result": "You've hit your session limit · resets 10:40pm"}]
            (run_dir / "records.json").write_text(json.dumps(old), encoding="utf-8")
            fake = _FakeSuite()
            with mock.patch.object(suites, "module", return_value=fake):
                tier1.run("eng-addy", yes_spend=True, resume=run_dir, log=lambda *_: None, ledger=False)
            self.assertNotIn("t-1__baseline__0", fake.calls)
            self.assertIn("t-1__upstream__0", fake.calls)

    def test_resume_redoes_a_cell_without_any_measured_metric(self):
        """An invalid grader reply leaves no score (Addy's run-evals.js records a failure); resume reruns the cell."""
        self.assertFalse(tier1._valid({"label": "x", "metrics": {"score": None}}))
        self.assertFalse(tier1._valid({"label": "x", "metrics": {}}))
        self.assertTrue(tier1._valid({"label": "x", "metrics": {"score": 0.0, "other": None}}))


class TestAgencyNotFirst(unittest.TestCase):
    def test_agency_files_never_rank_in_the_first_two(self):
        """MP3 §4: no Agency file is among an engineering/testing capability's first two sources, unless Agency is
        all it has (then there is nothing else to rank first)."""
        from agylite.benchmark.quality.tier0 import agency_in_first_two
        e = lambda p, kind="skill": {"path": p, "kind": kind, "tokens": 10, "name": p.split("/")[-2]}   # noqa: E731
        entries = [e("files/agency/testing/a.md", "doc"), e("files/ecc/skills/x/SKILL.md"), e("files/addy/skills/y/SKILL.md")]
        self.assertEqual(agency_in_first_two(entries, ["files/agency/testing/a.md"]), ["files/agency/testing/a.md"])
        self.assertEqual(agency_in_first_two(entries, ["files/ecc/skills/x/SKILL.md"]), [])
        self.assertEqual(agency_in_first_two([e("files/agency/testing/a.md", "doc")], []), [])


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


class TestLedger(unittest.TestCase):
    def test_append_writes_json_and_generated_markdown(self):
        import tempfile

        from agylite.benchmark.quality import ledger
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "docs" / "plan").mkdir(parents=True)
            rep = {"suite": "eng-addy", "date": "d", "runs": 1, "bundle": "b", "model": "m", "verdict": "near",
                   "metrics": {"expectations_passed": {"baseline": 0.5, "upstream": 1.0, "agylite": 0.9,
                                                        "retained": 0.8, "verdict": "near"}},
                   "cost_usd": {"baseline": 1.0, "upstream": 2.0, "agylite": 1.5}}
            ledger.append(rep, fix="none", next_step="diagnose", root=root)
            ledger.note("design-extract baseline waits for its instrument (Phase 5)", root=root)
            data = json.loads((root / ledger.JSON_PATH).read_text())
            self.assertEqual((len(data["rows"]), data["rows"][0]["verdict"]), (1, "near"))
            md = (root / ledger.MD_PATH).read_text()
            self.assertIn("| eng-addy | 1 |", md)
            self.assertIn("expectations_passed: 0.5 / 1 / 0.9 (0.8, near)", md)
            self.assertIn("design-extract baseline waits", md)


if __name__ == "__main__":
    unittest.main()
