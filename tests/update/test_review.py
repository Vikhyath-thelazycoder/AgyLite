"""MP6 §6: `agylite update --review` against a real temporary git upstream — per-commit classes, section diffs,
verdicts and proposals; review never activates; approve refuses a stale review; reject hides its range but counts it;
the bootstrap pending line needs no network."""
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

from tests.bundle.test_build import FILES, Fixture  # noqa: E402
from tests.update.test_track import git  # noqa: E402
from agylite.update import UpdateError  # noqa: E402
from agylite.update import review as rv  # noqa: E402

PRIORITIES = {"engineering/planning": ["files/alpha/skills/x/SKILL.md"]}
SKILL_V2 = FILES["skills/x/SKILL.md"] + "\n## Steps\n\nRead the reference first, then plan.\n"


class TestReview(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.up = self.tmp / "remote" / "demo" / "alpha.git"
        self.up.mkdir(parents=True)
        git("init", "-q", "-b", "main", cwd=self.up)
        self.write(FILES)
        self.sha0 = self.commit("initial")
        self.fx = Fixture(self.tmp)
        snap = self.fx.evidence / "upstream-staging-snapshot.yaml"
        snap.write_text(snap.read_text(encoding="utf-8").replace("a" * 40, self.sha0), encoding="utf-8")
        self.fx.build()
        self.env = mock.patch.dict(os.environ, {"AGYLITE_UPSTREAM_BASE": str(self.tmp / "remote")})
        self.env.start()
        # (a) primary file · (f) security fix on a bundled file · (b) rename a bundled file · (c) a new skill nobody
        # names · (d) excluded paths only · (e) an MCP config
        self.write({"skills/x/SKILL.md": SKILL_V2})
        self.a = self.commit("feat: add planning steps")
        self.write({"skills/x/references/r.md": "# Reference\nsame content\nNever print tokens.\n"})
        self.f = self.commit("fix: redact tokens in labels")
        git("mv", "docs/dup.md", "docs/dup2.md", cwd=self.up)
        self.b = self.commit("refactor: move docs")
        self.write({"extra/y/SKILL.md": "---\nname: y\ndescription: write release notes for a product launch\n---\n"})
        self.c = self.commit("feat: new skill y")
        self.write({"notes/excluded.md": "still not bundled\n"})
        self.d = self.commit("docs: notes")
        self.write({".mcp.json": '{"mcpServers": {}}\n'})
        self.e = self.commit("chore: add mcp config")

    def tearDown(self):
        self.env.stop()
        self._tmp.cleanup()

    def write(self, files):
        for rel, text in files.items():
            (self.up / rel).parent.mkdir(parents=True, exist_ok=True)
            (self.up / rel).write_text(text, encoding="utf-8")

    def commit(self, msg):
        git("add", "-A", cwd=self.up)
        git("commit", "-q", "-m", msg, cwd=self.up)
        return git("rev-parse", "HEAD", cwd=self.up)

    def current(self):
        return os.readlink(self.fx.home / "bundles" / "current")

    def review(self, to):
        return rv.review(self.fx.home, repos=["alpha"], to=to, out=self.tmp / f"review-{to[:7]}",
                         policy={"alpha": {"track": "weekly", "branch": "main"}}, staging=self.fx.staging,
                         evidence=self.fx.evidence, rules_path=self.fx.rules, licenses_path=self.fx.licenses,
                         priorities=PRIORITIES, run_tier0=False, check_registry=False, log=lambda *_: None)["upstreams"][0]

    def test_classes_per_commit(self):
        r = self.review(self.e)
        got = {c["sha"]: c["classes"] for c in r["commits"]}
        self.assertEqual(got[self.a], ["PRIMARY"])
        self.assertEqual(got[self.f], ["SECURITY", "BUNDLED"])
        self.assertIn("BREAKING", got[self.b])
        self.assertEqual(got[self.c], ["NEW_SKILL"])
        self.assertEqual(got[self.d], ["IRRELEVANT"])
        self.assertIn("POLICY", got[self.e])
        self.assertEqual({c["sha"]: c["type"] for c in r["commits"]}[self.b], "refactor")
        self.assertEqual(r["verdict"], "HOLD")                         # (e) the MCP config holds everything
        self.assertEqual(r["build"]["status"], "not-built")

    def test_primary_change_has_a_section_diff_and_needs_tier1(self):
        before = self.current()
        r = self.review(self.a)
        self.assertEqual(r["verdict"], "ADOPT_AFTER_TIER1", r["why"])
        self.assertEqual(r["build"]["status"], "candidate", r["build"])
        f = next(x for x in r["files"] if x["path"] == "skills/x/SKILL.md")
        self.assertEqual(f["primary"], "engineering/planning")
        self.assertEqual([s["id"] for s in f["added"]], ["steps"])
        self.assertTrue(any("Read the reference first" in line for line in f["diff"]))
        self.assertEqual(self.current(), before)                      # review never activates
        report = (self.tmp / f"review-{self.a[:7]}" / "REPORT.md").read_text(encoding="utf-8")
        self.assertIn("ADOPT_AFTER_TIER1", report)
        self.assertIn("agylite update --approve alpha@", report)

    def test_security_fast_track_wins_over_tier1(self):
        r = self.review(self.f)
        self.assertEqual(r["verdict"], "SECURITY_FAST_TRACK", r["why"])

    def test_rename_needs_rules_with_a_proposal(self):
        r = self.review(self.b)
        self.assertEqual(r["verdict"], "NEEDS_RULES")
        prop = next(p for p in r["proposals"] if p["kind"] == "rename")
        self.assertEqual((prop["old"], prop["new"]), ("docs/dup.md", "docs/dup2.md"))
        self.assertEqual(prop["rule"]["decision"], "COPY")
        patch = (self.tmp / f"review-{self.b[:7]}" / "alpha-proposed-rules.patch").read_text(encoding="utf-8")
        self.assertIn('+      - {paths: ["docs/dup2.md"]', patch)

    def test_new_skill_is_proposed_as_reference_with_capabilities(self):
        r = self.review(self.c)
        prop = next(p for p in r["proposals"] if p["kind"] == "new_skill")
        self.assertEqual(prop["rule"]["decision"], "REFERENCE")
        self.assertEqual(len(prop["candidates"]), 3)

    def test_approve_refuses_stale_then_switches(self):
        self.review(self.a)
        snap = self.fx.evidence / "upstream-staging-snapshot.yaml"
        good = snap.read_text(encoding="utf-8")
        snap.write_text(good.replace(self.sha0, "b" * 40), encoding="utf-8")   # a pin moved after the review
        with self.assertRaisesRegex(UpdateError, "review is stale"):
            rv.approve(self.fx.home, "alpha", evidence=self.fx.evidence)
        snap.write_text(good, encoding="utf-8")
        before = self.current()
        r = rv.approve(self.fx.home, "alpha", self.a[:7], evidence=self.fx.evidence)
        self.assertEqual(r["status"], "activated")
        self.assertNotEqual(self.current(), before)
        self.assertEqual(rv.pending(self.fx.home), [])
        decisions = (self.fx.home / "updates" / "decisions.jsonl").read_text(encoding="utf-8")
        self.assertIn('"verdict": "ADOPT_AFTER_TIER1"', decisions)

    def test_held_candidates_cannot_be_approved(self):
        self.review(self.e)
        with self.assertRaisesRegex(UpdateError, "cannot be approved"):
            rv.approve(self.fx.home, "alpha", evidence=self.fx.evidence)

    def test_reject_hides_the_range_but_counts_it(self):
        self.review(self.f)
        rv.reject(self.fx.home, "alpha", self.f[:7], "not now")
        r = self.review(self.e)
        self.assertEqual(r["rejected_commits"], 2)
        self.assertNotIn(self.a, [c["sha"] for c in r["commits"]])
        self.assertIn("2 previously rejected", (self.tmp / f"review-{self.e[:7]}" / "REPORT.md").read_text("utf-8"))

    def test_pending_line_needs_no_network(self):
        self.review(self.a)
        real = subprocess.run

        def no_network(argv, *a, **kw):
            if "ls-remote" in argv or "fetch" in argv:
                raise AssertionError("network at session start")
            return real(argv, *a, **kw)
        with mock.patch("subprocess.run", no_network):
            line = rv.pending_line(self.fx.home)
        self.assertEqual(line, "updates: 1 reviewed upstream update(s) awaiting approval (agylite update --pending)")

    def test_report_json_and_unmatched_groups(self):
        ev = self.fx.home / "projects" / "p1" / "events"
        ev.mkdir(parents=True)
        (ev / "2026-10-22.jsonl").write_text("".join(json.dumps(
            {"event": "ROUTE_UNMATCHED", "ts": "2999-01-01T00:00:00+00:00", "details": {"keywords": ["podcast", "rss"]}})
            + "\n" for _ in range(2)), encoding="utf-8")
        self.review(self.a)
        data = json.loads((self.tmp / f"review-{self.a[:7]}" / "report.json").read_text(encoding="utf-8"))
        self.assertEqual(data["unmatched"], [{"words": ["podcast", "rss"], "count": 2}])


class TestHelpers(unittest.TestCase):
    def test_section_diff(self):
        old = "# T\n\n## A\none\n\n## B\ntwo\n"
        new = "# T\n\n## A\none, changed\n\n## C\nthree\n"
        d = rv.section_diff(old, new, full=True)
        self.assertEqual([x["id"] for x in d["changed"]], ["a"])
        self.assertEqual([x["id"] for x in d["added"]], ["c"])
        self.assertEqual([x["id"] for x in d["removed"]], ["b"])
        self.assertTrue(any(l.startswith("+one, changed") for l in d["diff"]))

    def test_changelog_between(self):
        text = "# Changelog\n\n## 1.3.0\n- new\n\n## 1.2.0\n- mid\n\n## 1.1.0\n- old\n"
        self.assertEqual(rv.changelog_between(text, "1.1.0", "1.3.0"), "## 1.3.0\n- new\n\n## 1.2.0\n- mid")

    def test_verdict_precedence(self):
        from collections import Counter
        self.assertEqual(rv.verdict(Counter(POLICY=1, SECURITY=1), "candidate", [])[0], "HOLD")
        self.assertEqual(rv.verdict(Counter(BREAKING=1), None, [])[0], "NEEDS_RULES")
        self.assertEqual(rv.verdict(Counter(PRIMARY=1), "failed", [])[0], "HOLD")
        self.assertEqual(rv.verdict(Counter(BUNDLED=1), "candidate", ["routing: x"])[0], "HOLD")
        self.assertEqual(rv.verdict(Counter(IRRELEVANT=3), "candidate", [])[0], "SKIP")
        self.assertEqual(rv.verdict(Counter(BUNDLED=1), "candidate", [])[0], "ADOPT")
        self.assertEqual(rv.verdict(Counter(PRIMARY=1), "candidate", [])[0], "ADOPT_AFTER_TIER1")
        self.assertEqual(rv.verdict(Counter(PRIMARY=1, SECURITY=1), "candidate", [])[0], "SECURITY_FAST_TRACK")

    def test_suites_for_capabilities(self):
        self.assertEqual(rv.suites_for(["engineering/review", "design/frontend", "youtube/script"]),
                         ["eng-ponytail", "design-taste", "youtube"])


if __name__ == "__main__":
    unittest.main()
