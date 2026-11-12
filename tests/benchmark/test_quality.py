"""MP2 §6: the quality harness itself — scoring math, isolation check, dry run / spend control, suite schemas."""
import json
import os
import re
import shutil
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


class TestReuseArms(unittest.TestCase):
    def test_reuse_keeps_unchanged_arms_and_reruns_the_named_ones(self):
        """IMPLEMENTATION_PLAN §2.4 "never re-run an unchanged configuration": a new AgyLite build re-runs only the
        AgyLite arm (and any cell the earlier run lacks); no-skill and original results come from the earlier run,
        copied into a new run directory (the earlier run is never modified)."""
        with tempfile.TemporaryDirectory() as tmp:
            old = Path(tmp) / "old"
            old.mkdir()
            prev = [{"label": f"t-1__{a}__0", "arm": a, "task": "t#1", "run": 0, "metrics": {"score": 0.5}}
                    for a in ("baseline", "upstream", "agylite")]
            (old / "records.json").write_text(json.dumps(prev), encoding="utf-8")
            fake = _FakeSuite()
            with mock.patch.object(suites, "module", return_value=fake):
                rep = tier1.run("eng-addy", arms=("agylite",), yes_spend=True, reuse_from=old, out_root=Path(tmp),
                                log=lambda *_: None, ledger=False)
            self.assertEqual(fake.calls, ["t-1__agylite__0", "t-2__baseline__0", "t-2__upstream__0", "t-2__agylite__0"])
            self.assertNotEqual(rep["run_dir"], str(old))
            self.assertEqual(rep["sessions"], 6)
            self.assertEqual(rep["reused_from"], str(old))
            self.assertEqual(json.loads((old / "records.json").read_text())[2]["metrics"], {"score": 0.5})
            with mock.patch.object(suites, "module", return_value=_FakeSuite()):   # the dry run counts the same cells
                dry = tier1.run("eng-addy", arms=("agylite",), dry_run=True, reuse_from=old, log=lambda *_: None)
            self.assertEqual((dry["planned"], dry["reused"]), (4, 2))


class TestAgencyNotFirst(unittest.TestCase):
    def test_agency_files_never_rank_in_the_first_two(self):
        """MP3 §4: no Agency file is among an engineering/testing capability's first two sources ahead of a non-Agency
        source; when the capability has fewer than two non-Agency sources, Agency may only follow all of them."""
        from agylite.benchmark.quality.tier0 import agency_in_first_two
        e = lambda p, kind="skill": {"path": p, "kind": kind, "tokens": 10, "name": p.split("/")[-2]}   # noqa: E731
        entries = [e("files/agency/testing/a.md", "doc"), e("files/ecc/skills/x/SKILL.md"), e("files/addy/skills/y/SKILL.md")]
        self.assertEqual(agency_in_first_two(entries, ["files/agency/testing/a.md"]), ["files/agency/testing/a.md"])
        self.assertEqual(agency_in_first_two(entries, ["files/ecc/skills/x/SKILL.md"]), [])
        self.assertEqual(agency_in_first_two([e("files/agency/testing/a.md", "doc")], []), [])
        two = [e("files/agency/testing/a.md", "doc"), e("files/ecc/skills/x/SKILL.md")]   # testing/local-verification
        self.assertEqual(agency_in_first_two(two, ["files/ecc/skills/x/SKILL.md"]), [])
        self.assertEqual(agency_in_first_two(two, ["files/agency/testing/a.md"]), ["files/agency/testing/a.md"])


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


class TestDesignExtractSuite(unittest.TestCase):
    """design-extract: designlang's bench ground truth and score.js, the original CLI against the AgyLite wrapper."""

    def setUp(self):
        from agylite.benchmark.quality.suites import extract_runner
        self.m = extract_runner

    def test_cells_are_the_suite_sites_and_baseline_runs_nothing(self):
        cfg = suites.load_suite("design-extract")
        self.assertEqual([c["site"] for c in self.m.cells(cfg)], cfg["tasks"])
        with mock.patch("subprocess.run") as run:
            rec = self.m.run_cell({"task": "stripe.com", "site": "stripe.com"},
                                  {"arm": "baseline", "label": "stripe.com__baseline__0", "run_dir": "/nonexistent"})
        run.assert_not_called()
        self.assertEqual(rec["metrics"], {"color_hit": 0, "font_hit": 0, "design_md_sections": 0})

    def test_sections_counts_the_eight_design_md_headings(self):
        md = "---\nsite: x\n---\n\n# Overview\n\n# Colors\n## Colors sub\n# Shapes\n# Not a section\n"
        self.assertEqual(self.m.sections(md), 3)

    @unittest.skipUnless(shutil.which("node") and (suites.upstreams_dir() / "design-extract" / "bench" / "score.js")
                         .is_file(), "node or the design-extract clone not present")
    def test_hits_use_score_js_and_skip_dimensions_without_truth(self):
        truth = {"primary": ["#533afd"], "font": ["sohne-var", "Söhne"]}
        self.assertEqual(self.m.hits("#5339fc", "Sohne", truth), {"color": True, "font": True})
        self.assertEqual(self.m.hits("#ff0000", None, truth), {"color": False, "font": False})
        self.assertEqual(self.m.hits("#000000", "Geist", {"primary": [], "font": ["Geist"]}),
                         {"color": None, "font": True})


def _tool(name, **inp):
    return json.dumps({"type": "assistant", "message": {"content": [{"type": "tool_use", "name": name, "input": inp}]}})


class TestMeasurementFixes(unittest.TestCase):
    """Step 3 part 1 (PARITY_REPORT fix order 1): numbers a later run can trust — C1-1, C3-2, C3-1, C3-7, C1-9."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name).resolve()
        self.home = self.base / "home"
        self.sources = [self.home / "Developer" / "os", self.home / ".claude" / "plugins", self.home / ".claude" / "skills",
                        self.home / ".agylite"]
        for s in self.sources:
            s.mkdir(parents=True)
        self.ws = self.base / "ws"
        self.ws.mkdir()
        patcher = mock.patch.object(harness, "skill_sources", return_value=self.sources)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(self.tmp.cleanup)

    # C1-1: the AgyLite arm runs the snapshot under test, never an installed engine
    def test_launcher_skips_central_install_and_path_when_pinned_to_the_plugin_source(self):
        fake = self.base / "fake"
        (fake / "core" / "bin").mkdir(parents=True)
        (fake / "path").mkdir()
        for exe, word in ((fake / "core" / "bin" / "agylite", "CORE"), (fake / "path" / "agylite", "ONPATH")):
            exe.write_text(f"#!/bin/sh\necho {word}\n", encoding="utf-8")
            exe.chmod(0o755)
        env = {**os.environ, "AGYLITE_HOME": str(fake), "PATH": f"{fake / 'path'}{os.pathsep}{os.environ['PATH']}"}
        env.pop("AGYLITE_PLUGIN_SOURCE", None)   # the caller's own pin (e.g. `agylite validate` under it) must not leak in
        launcher = os.path.join(ROOT_DIR, "bin", "agylite")
        import subprocess
        plain = subprocess.run([launcher, "--help"], env=env, capture_output=True, text=True)
        self.assertIn("CORE", plain.stdout)
        pinned = subprocess.run([launcher, "--help"], env={**env, "AGYLITE_PLUGIN_SOURCE": "1"}, capture_output=True,
                                text=True)
        self.assertNotIn("CORE", pinned.stdout + pinned.stderr)
        self.assertNotIn("ONPATH", pinned.stdout + pinned.stderr)

    def test_agylite_arm_pins_the_launcher(self):
        with mock.patch.object(harness, "plugin_snapshot", return_value=self.base / "snap"):
            arm = harness.agylite_arm(self.base / "run")
        self.assertEqual(arm.env["AGYLITE_PLUGIN_SOURCE"], "1")

    def test_engine_check_fails_a_session_run_by_another_engine(self):
        snap = self.base / "run" / "agylite-plugin"
        snap.mkdir(parents=True)
        log = self.base / "agyhome" / "projects" / "p" / "events" / "2026-11-10.jsonl"
        log.parent.mkdir(parents=True)

        def usage(engine):
            details = {"root": str(self.ws)} | ({"engine": engine} if engine else {})
            log.write_text(json.dumps({"event": "SESSION_STARTED", "details": details}) + "\n", encoding="utf-8")
            return harness.agylite_usage(self.base / "agyhome", self.ws)

        self.assertIsNone(harness.engine_error(usage(str(snap)), snap))
        self.assertIn("not the snapshot", harness.engine_error(usage("/Users/x/.agylite/core/src"), snap))
        self.assertIn("not the snapshot", harness.engine_error(usage(None), snap))   # old engines write no engine
        log.write_text("", encoding="utf-8")
        self.assertIn("never started", harness.engine_error(harness.agylite_usage(self.base / "agyhome", self.ws), snap))

    # C3-2: no arm reads skill sources it does not use
    def test_flags_reads_and_home_searches_of_skill_sources(self):
        base = harness.ArmSetup("baseline")
        leaks = harness.skill_source_reads([
            _tool("Read", file_path=str(self.ws / "app.py")),
            _tool("Read", file_path=str(self.home / ".agylite" / "bundles" / "b" / "files" / "archify" / "SKILL.md")),
            _tool("Bash", command=f"cat {self.home}/.claude/plugins/cache/x/SKILL.md | head"),
            _tool("Bash", command=f"find {self.home} -name '*archify*' 2>/dev/null"),
            _tool("Glob", pattern="**/SKILL.md", path=str(self.home / "Developer")),
            _tool("Bash", command="ls -la && cat app.py"),
        ], base, self.ws)
        self.assertEqual(len(leaks), 4, leaks)
        self.assertFalse(any("app.py" in x for x in leaks))

    def test_an_arm_may_read_its_own_sources(self):
        plugin = self.sources[0] / "archify"
        plugin.mkdir()
        up = harness.ArmSetup("upstream", args=["--plugin-dir", str(plugin)])
        self.assertEqual(harness.skill_source_reads([_tool("Read", file_path=str(plugin / "SKILL.md"))], up, self.ws), [])
        qa = harness.ArmSetup("upstream", reads=(str(self.sources[2] / "gstack"),))
        self.assertEqual(harness.skill_source_reads(
            [_tool("Bash", command=f"{self.sources[2]}/gstack/browse/dist/browse goto x")], qa, self.ws), [])
        self.assertEqual(len(harness.skill_source_reads(
            [_tool("Read", file_path=str(self.sources[2] / "other" / "SKILL.md"))], qa, self.ws)), 1)

    def test_deny_rules_hide_unused_sources_and_keep_the_arms_own(self):
        plugin = self.sources[0] / "archify"
        (self.sources[0] / "taste").mkdir(parents=True)
        plugin.mkdir()
        rules = harness.skill_source_denies(harness.ArmSetup("upstream", args=["--plugin-dir", str(plugin)]), self.ws)
        self.assertIn(f"Read(/{self.sources[0] / 'taste'}/**)", rules)
        self.assertIn(f"Read(/{self.sources[1]}/**)", rules)
        self.assertFalse(any("archify" in r for r in rules))
        self.assertNotIn(f"Read(/{self.sources[0]}/**)", rules)

    def test_run_session_passes_the_deny_rules_and_records_a_leak(self):
        trace = "\n".join([_init([]), _tool("Read", file_path=str(self.home / ".claude" / "skills" / "x" / "SKILL.md")),
                           json.dumps({"type": "result", "result": "done", "total_cost_usd": 0.1, "num_turns": 2})])
        with mock.patch("subprocess.run", return_value=mock.Mock(stdout=trace, returncode=0)) as run:
            rec = harness.run_session("p", self.ws, harness.ArmSetup("baseline"))
        cmd = run.call_args.args[0]
        self.assertIn("--disallowedTools", cmd)
        self.assertIn(f"Read(/{self.sources[2]}/**)", cmd[cmd.index("--disallowedTools") + 1])
        self.assertIn("skill source", rec["isolation_error"])
        self.assertFalse(tier1._valid({**rec, "metrics": {"score": 1}}))

    def test_browser_qa_arms_may_read_gstacks_own_install(self):
        from agylite.benchmark.quality.suites import browser_qa_runner as bq
        self.assertEqual(bq._upstream_arm().reads, bq.GSTACK_READS)
        with mock.patch.object(harness, "run_session", return_value={"result": ""}) as run, \
                mock.patch.object(harness, "plugin_snapshot", return_value=self.base / "snap"), \
                mock.patch.object(bq, "remaining", return_value=[]):
            bq.run_cell({"task": "t"}, {"arm": "agylite", "run_dir": self.base / "run", "model": "m", "label": "l"})
        self.assertEqual(run.call_args.args[2].reads, bq.GSTACK_READS)

    # C3-1: the inspector's FAIL count comes from its saved report, not a possibly cut stdout
    def test_taste_measure_reads_report_json(self):
        from agylite.benchmark.quality.suites import taste_runner
        page = self.base / "site" / "index.html"
        page.parent.mkdir()
        page.write_text("<html></html>", encoding="utf-8")
        out = self.base / "out"

        def node(script, *args, cwd, tmp):
            if script == "inspect.mjs":
                shots = Path(args[args.index("--out") + 1])
                shots.mkdir(parents=True, exist_ok=True)
                (shots / "report.json").write_text(json.dumps({"findings": [
                    {"level": "FAIL", "id": "a"}, {"level": "FAIL", "id": "b"}, {"level": "WARN", "id": "c"}]}))
                return mock.Mock(stdout='{"findings": [{"level": "FAIL"', stderr="")   # cut off mid-JSON
            return mock.Mock(stdout='{"findings": []}', stderr="")

        with mock.patch.object(taste_runner, "_node", side_effect=node):
            m = taste_runner.measure(page, out, False, self.base / "t")
        self.assertEqual((m["inspector_fail"], m["lint_fail"]), (2, 0))

    # C3-7 + C1-9: the report counts cells that did not really run their skill or asked instead of acting
    def test_report_counts_skill_not_used_and_asked_instead_of_acting(self):
        ask = json.dumps({"type": "result", "result": "Before I write a test: which seam should I use?",
                          "total_cost_usd": 0.1, "num_turns": 1})
        acted = "\n".join([_tool("Edit", file_path="a.py"), json.dumps({"type": "result", "result": "Fixed. Want more?"})])
        self.assertTrue(harness.summarize_trace([ask])["asked"])
        self.assertFalse(harness.summarize_trace(acted.splitlines())["asked"])

        class Mod:
            METRICS = {"score": False}
        recs = [{"label": "t__upstream__0", "arm": "upstream", "task": "t", "metrics": {"score": 1}, "skill_loads": ["x"]},
                {"label": "t__upstream__1", "arm": "upstream", "task": "t", "metrics": {"score": 0}, "skill_loads": []},
                {"label": "t__agylite__0", "arm": "agylite", "task": "t", "metrics": {"score": 0}, "skill_loads": [],
                 "asked_instead_of_acting": True},
                {"label": "t__baseline__0", "arm": "baseline", "task": "t", "metrics": {"score": 0}, "skill_loads": []}]
        rep = tier1.score("s", {}, Mod, recs)
        self.assertEqual(rep["skill_not_used"], ["t__upstream__1"])
        self.assertEqual(rep["asked_instead_of_acting"], ["t__agylite__0"])
        self.assertIn("asked instead of acting", tier1.render({**rep, "runs": 1, "model": "m"}))
        # a suite whose original never uses the Skill tool (Addy/Pocock: system prompt) reports nothing
        self.assertEqual(tier1.score("s", {}, Mod, [r | {"skill_loads": []} for r in recs])["skill_not_used"], [])

    def test_action_tasks_flag_questions_only_where_the_suite_expects_action(self):
        rec = {"label": "l", "arm": "upstream", "metrics": {"score": 0}, "asked": True}
        self.assertTrue(tier1.mark_asked(dict(rec), {"acts": True})["asked_instead_of_acting"])
        self.assertNotIn("asked_instead_of_acting", tier1.mark_asked(dict(rec), {"task": "grilling#1"}))
        acts = {t["skill"] + "#" + str(t["eval"]) for t in suites.load_suite("eng-pocock")["tasks"] if t.get("acts")}
        self.assertEqual(acts, {"tdd#1", "tdd#2", "diagnosing-bugs#1", "diagnosing-bugs#2", "to-tickets#2"})


if __name__ == "__main__":
    unittest.main()
