"""P28 (D-047): upstream tracking with real local git repositories as upstreams — check finds new commits, latest
applies them through the checked pipeline using an incremental mirror, policies (due/manual/releases) hold, a broken
upstream commit never switches, promote writes pins back, the weekly job is opt-in."""
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.insert(0, ROOT_DIR)

from tests.bundle.test_build import FILES, Fixture  # noqa: E402
from agylite.update import track  # noqa: E402


def git(*args, cwd):
    return subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t", *args], cwd=cwd, check=True,
                          capture_output=True, text=True).stdout.strip()


class Base(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.upstream = self.tmp / "remote" / "demo" / "alpha.git"
        self.upstream.mkdir(parents=True)
        git("init", "-q", "-b", "main", cwd=self.upstream)
        self.write(FILES)
        self.sha1 = self.commit("initial")
        self.fx = Fixture(self.tmp)
        snap = self.fx.evidence / "upstream-staging-snapshot.yaml"
        snap.write_text(snap.read_text(encoding="utf-8").replace("a" * 40, self.sha1), encoding="utf-8")
        self.fx.build()
        self.env = mock.patch.dict(os.environ, {"AGYLITE_UPSTREAM_BASE": str(self.tmp / "remote")})
        self.env.start()
        self.policy = {"alpha": {"track": "weekly", "branch": "main"}}

    def tearDown(self):
        self.env.stop()
        self._tmp.cleanup()

    def write(self, files):
        for rel, text in files.items():
            (self.upstream / rel).parent.mkdir(parents=True, exist_ok=True)
            (self.upstream / rel).write_text(text, encoding="utf-8")

    def commit(self, msg):
        git("add", "-A", cwd=self.upstream)
        git("commit", "-q", "-m", msg, cwd=self.upstream)
        return git("rev-parse", "HEAD", cwd=self.upstream)

    def current(self):
        return os.readlink(self.fx.home / "bundles" / "current")

    def latest(self, activate=True, **kw):   # explicit activation; the default never switches (MP6)
        return track.latest(self.fx.home, policy=self.policy, staging=self.fx.staging, evidence=self.fx.evidence,
                            rules_path=self.fx.rules, licenses_path=self.fx.licenses, check_registry=False,
                            activate=activate, log=lambda *_: None, **kw)


class TestTracking(Base):
    def test_check_records_when_a_pin_was_found_current(self):
        """F9 follow-up: doctor counts a pin as fresh from the last check that found it current."""
        rows = track.check(self.fx.home, evidence=self.fx.evidence, policy=self.policy)
        self.assertEqual(rows[0]["status"], "up-to-date")
        self.assertIn("checked_current", track._state(self.fx.home)["alpha"])
        self.write({"skills/new.md": "x\n"})
        self.commit("new")
        track._save_state(self.fx.home, {})
        track.check(self.fx.home, evidence=self.fx.evidence, policy=self.policy)
        self.assertNotIn("alpha", track._state(self.fx.home))

    def test_check_then_latest_applies_new_commit_via_mirror(self):
        rows = track.check(self.fx.home, evidence=self.fx.evidence, policy=self.policy)
        self.assertEqual(rows[0]["status"], "up-to-date")
        self.write({"skills/x/SKILL.md": FILES["skills/x/SKILL.md"] + "Newer guidance.\n"})
        sha2 = self.commit("update skill")
        rows = track.check(self.fx.home, evidence=self.fx.evidence, policy=self.policy)
        self.assertEqual((rows[0]["status"], rows[0]["latest"]), ("update-available", sha2))
        before = self.current()
        res = self.latest()[0]
        self.assertEqual(res["action"], "activated", res.get("errors"))
        self.assertEqual(res["commits"], 1)
        self.assertEqual(res["diff"]["bundled_changed"], ["skills/x/SKILL.md"])
        self.assertNotEqual(self.current(), before)
        mirror = self.fx.home / "mirrors" / "demo__alpha.git"
        self.assertTrue((mirror / "HEAD").is_file())
        self.assertEqual(self.latest()[0]["action"], "none")                    # nothing new now
        # a further upstream commit: the mirror only fetches the new commit
        self.write({"docs/dup.md": FILES["docs/dup.md"] + "more\n"})
        sha3 = self.commit("docs")
        res = self.latest()[0]
        self.assertEqual(res["action"], "activated", res.get("errors"))
        git("cat-file", "-e", f"{sha3}^{{commit}}", cwd=mirror)
        self.assertIn(sha3, (self.fx.home / "bundles" / "current" / "evidence" / "upstream-staging-snapshot.yaml")
                      .read_text(encoding="utf-8"))

    def test_latest_never_activates_by_default(self):
        """MP6: nothing activates automatically; the default builds and checks a candidate only."""
        self.write({"docs/dup.md": FILES["docs/dup.md"] + "more\n"})
        self.commit("docs")
        before = self.current()
        res = self.latest(activate=False)[0]
        self.assertEqual(res["action"], "candidate", res.get("errors"))
        self.assertEqual(self.current(), before)

    def test_broken_upstream_commit_never_switches(self):
        (self.upstream / "skills/x/references/r.md").unlink()
        self.commit("remove referenced file")
        before = self.current()
        res = self.latest()[0]
        self.assertEqual(res["action"], "failed")
        self.assertTrue(any("dangling reference" in e for e in res["errors"]), res["errors"])
        self.assertEqual(self.current(), before)

    def test_policies_due_manual_and_releases(self):
        self.write({"docs/dup.md": "x\n"})
        self.commit("change")
        state = {"alpha": {"applied_check": datetime.now(timezone.utc).isoformat()}}
        self.assertFalse(track.due("alpha", {"track": "weekly"}, state))
        old = (datetime.now(timezone.utc) - timedelta(days=8)).isoformat()
        self.assertTrue(track.due("alpha", {"track": "weekly"}, {"alpha": {"applied_check": old}}))
        self.assertFalse(track.due("alpha", {"track": "monthly"}, {"alpha": {"applied_check": old}}))
        self.assertFalse(track.due("alpha", {"track": "manual"}, {}))
        self.policy = {"alpha": {"track": "manual", "branch": "main"}}
        self.assertEqual(self.latest()[0]["action"], "skipped")
        git("tag", "v1.0.0", self.sha1, cwd=self.upstream)
        git("tag", "-a", "v1.2.0", "-m", "release", cwd=self.upstream)
        head = git("rev-parse", "HEAD", cwd=self.upstream)
        self.assertEqual(track.remote_latest("demo/alpha", {"track": "releases"}), head)

    def test_promote_and_schedule(self):
        self.write({"docs/dup.md": "promoted\n"})
        sha2 = self.commit("change")
        self.assertEqual(self.latest()[0]["action"], "activated")
        repo_ev = self.tmp / "repo-evidence"
        import shutil
        shutil.copytree(self.fx.evidence, repo_ev)
        self.assertEqual(track.promote(self.fx.home, repo_ev), ["alpha"])
        self.assertIn(sha2, (repo_ev / "upstream-staging-snapshot.yaml").read_text(encoding="utf-8"))
        self.assertTrue((repo_ev / "upstream-file-hashes" / "alpha.tsv").read_text(encoding="utf-8")
                        .startswith(f"# alpha @ {sha2}"))
        user = self.tmp / "user"
        plist = track.schedule(self.fx.home, True, user_home=user, load=False)
        text = plist.read_text(encoding="utf-8")
        self.assertIn("<string>--latest</string><string>--due</string>", text)
        self.assertIn("<key>Weekday</key><integer>1</integer>", text)
        track.schedule(self.fx.home, False, user_home=user, load=False)
        self.assertFalse(plist.exists())

    def test_real_policy_file_covers_every_upstream(self):
        import yaml
        pins = yaml.safe_load((Path(ROOT_DIR) / "docs/audit/evidence/upstream-staging-snapshot.yaml")
                              .read_text(encoding="utf-8"))["snapshots"]
        policy = track.load_policy()
        self.assertEqual(set(policy), set(pins))
        for name, pol in policy.items():
            self.assertIn(pol["track"], ("weekly", "monthly", "manual", "releases"), name)
            self.assertEqual(pol.get("branch"), pins[name].get("branch"), name)


if __name__ == "__main__":
    unittest.main()
