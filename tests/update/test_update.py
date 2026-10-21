"""P24 acceptance (doc 16, D-045): an update builds a new bundle and switches only if every check passes; a broken
or interrupted update leaves `current` untouched; rollback restores a known-good bundle; gc keeps what matters."""
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.insert(0, ROOT_DIR)

from tests.bundle.test_build import FILES, Fixture  # noqa: E402
from agylite.bundle import build as bundle_build  # noqa: E402
from agylite.update import UpdateError, gc, rollback, update  # noqa: E402
from agylite.update.core import git_blob_sha1, inventory_from_dir  # noqa: E402

NEW_SHA = "b" * 40


class Base(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.fx = Fixture(self.tmp)
        self.old = self.fx.build()["bundle_id"]

    def tearDown(self):
        self._tmp.cleanup()

    def current(self):
        return os.readlink(self.fx.home / "bundles" / "current")

    def tree(self, files):
        d = self.tmp / f"src-{len(list(self.tmp.glob('src-*')))}"
        for path, text in files.items():
            (d / path).parent.mkdir(parents=True, exist_ok=True)
            (d / path).write_text(text, encoding="utf-8")
        return d

    def run_update(self, files, sha=NEW_SHA):
        return update(self.fx.home, "alpha", sha, source=self.tree(files), staging=self.fx.staging,
                      evidence=self.fx.evidence, rules_path=self.fx.rules, licenses_path=self.fx.licenses,
                      check_registry=False, log=lambda *_: None)   # fixture rules seat 1 of the real capabilities


class TestUpdate(Base):
    def test_good_update_switches_and_keeps_previous(self):
        files = dict(FILES)
        files["skills/x/SKILL.md"] = FILES["skills/x/SKILL.md"] + "New guidance line.\n"
        r = self.run_update(files)
        self.assertEqual(r["status"], "activated", r.get("errors"))
        self.assertNotEqual(r["bundle_id"], self.old)
        self.assertEqual(self.current(), r["bundle_id"])
        self.assertEqual(os.readlink(self.fx.home / "bundles" / "previous"), self.old)
        self.assertEqual(r["diff"]["bundled_changed"], ["skills/x/SKILL.md"])
        self.assertEqual(r["diff"]["capabilities_affected"], ["engineering/planning"])
        ev = self.fx.home / "bundles" / r["bundle_id"] / "evidence" / "upstream-staging-snapshot.yaml"
        self.assertIn(NEW_SHA, ev.read_text(encoding="utf-8"))    # the bundle records its own pins
        self.assertNotIn(NEW_SHA, (self.fx.evidence / "upstream-staging-snapshot.yaml").read_text(encoding="utf-8"))
        self.assertTrue((self.fx.home / "updates" / "history.jsonl").is_file())

    def test_broken_update_leaves_current_untouched(self):
        files = dict(FILES)
        del files["skills/x/references/r.md"]          # still referenced by the bundled SKILL.md
        r = self.run_update(files)
        self.assertEqual(r["status"], "failed")
        self.assertTrue(any("dangling reference" in e and "references/r.md" in e for e in r["errors"]), r["errors"])
        self.assertEqual(self.current(), self.old)

    def test_interrupted_build_leaves_current_untouched(self):
        files = dict(FILES)
        files["skills/x/SKILL.md"] += "changed\n"
        with mock.patch.object(bundle_build.Transformer, "apply", side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                self.run_update(files)
        self.assertEqual(self.current(), self.old)
        self.assertEqual(bundle_build.verify(self.fx.home / "bundles" / self.old), [])

    def test_rejects_moving_refs_and_unknown_repos(self):
        with self.assertRaises(UpdateError):
            self.run_update(FILES, sha="main")
        with self.assertRaises(UpdateError):
            update(self.fx.home, "nope", NEW_SHA, source=self.tree(FILES), staging=self.fx.staging,
                   evidence=self.fx.evidence, rules_path=self.fx.rules, licenses_path=self.fx.licenses)


class TestInventoryFromDir(unittest.TestCase):
    def test_symlink_is_one_blob_of_its_target_like_git(self):
        """F8: Brag's .agents/skills/brag is a symlink to skills/brag; git records one blob (the link target), not a
        copy of the directory it points to."""
        with tempfile.TemporaryDirectory() as tmp:
            tree = Path(tmp)
            (tree / "skills" / "brag").mkdir(parents=True)
            (tree / "skills" / "brag" / "SKILL.md").write_text("# brag\n")
            (tree / ".agents" / "skills").mkdir(parents=True)
            os.symlink("../../skills/brag", tree / ".agents" / "skills" / "brag")
            rows = inventory_from_dir(tree)
        self.assertEqual([r[0] for r in rows], [".agents/skills/brag", "skills/brag/SKILL.md"])
        link = rows[0]
        self.assertEqual(link[1:], (len(b"../../skills/brag"), git_blob_sha1(b"../../skills/brag")))


class TestRollbackAndGc(Base):
    def test_rollback_restores_previous_and_refuses_damaged(self):
        files = dict(FILES)
        files["skills/x/SKILL.md"] += "v2\n"
        new = self.run_update(files)["bundle_id"]
        r = rollback(self.fx.home)
        self.assertEqual((r["from"], r["to"]), (new, self.old))
        self.assertEqual(self.current(), self.old)
        target = self.fx.home / "bundles" / new
        next(p for p in (target / "files").rglob("SKILL.md")).write_text("tampered", encoding="utf-8")
        with self.assertRaises(UpdateError):
            rollback(self.fx.home, to=new)
        self.assertEqual(self.current(), self.old)

    def test_gc_keeps_current_previous_and_recent_failed(self):
        ids = []
        for i in range(3):
            files = dict(FILES)
            files["skills/x/SKILL.md"] += f"rev {i}\n"
            ids.append(self.run_update(files, sha=f"{i}" * 40)["bundle_id"])
        (self.fx.home / "runtimes" / "seo-deadbeef0000").mkdir(parents=True)
        dry = gc(self.fx.home, dry_run=True)
        self.assertEqual(set(dry["kept"]), {ids[-1], ids[-2]})
        self.assertEqual(set(dry["removed_bundles"]), {self.old, ids[0]})
        self.assertTrue((self.fx.home / "bundles" / self.old).is_dir())
        done = gc(self.fx.home)
        self.assertFalse((self.fx.home / "bundles" / self.old).exists())
        self.assertIn("seo-deadbeef0000", done["removed_runtimes"])
        self.assertEqual(self.current(), ids[-1])
        shutil.rmtree(self.fx.home / "updates", ignore_errors=True)


if __name__ == "__main__":
    unittest.main()


class TestSequentialUpdatesAcrossUpstreams(unittest.TestCase):
    """P28 live finding: after upstream A is updated, building B must use A's NEW tree (its pin moved), not the
    original staging snapshot."""

    def test_second_upstream_builds_with_first_upstreams_new_tree(self):
        import json
        from tests.bundle.test_build import SHA
        from agylite.bundle.store import git_blob_sha1
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            staging, evidence, home = tmp / "staging", tmp / "evidence", tmp / "home"
            (evidence / "upstream-file-hashes").mkdir(parents=True)
            rules = "version: 1\nrepos:\n"
            licenses, snaps = {}, []
            for name in ("alpha", "beta"):
                for path, text in FILES.items():
                    (staging / name / path).parent.mkdir(parents=True, exist_ok=True)
                    (staging / name / path).write_text(text, encoding="utf-8")
                rows = [f"{git_blob_sha1(x.encode())}\t{len(x.encode())}\t{p}" for p, x in sorted(FILES.items())]
                (evidence / "upstream-file-hashes" / f"{name}.tsv").write_text(
                    f"# {name} @ {SHA}\nblob_sha1\tbytes\tpath\n" + "\n".join(rows) + "\n", encoding="utf-8")
                rules += (f"  {name}:\n    default: {{decision: EXCLUDE, reason: OUT_OF_DOMAIN}}\n    rules:\n"
                          f"      - {{paths: [\"LICENSE\"], decision: COPY, capability: engineering/planning, reason: LICENSE}}\n"
                          f"      - {{paths: [\"skills/**\"], decision: ADAPT, capability: engineering/planning, reason: demo}}\n")
                licenses[name] = {"license": "MIT", "attribution": "x", "license_files": ["LICENSE"], "note": None,
                                  "repository": f"demo/{name}", "commit_sha": SHA, "bundled_files": 3}
                snaps.append(f"  {name}: {{repo: demo/{name}, head: {SHA}}}")
            (evidence / "upstream-staging-snapshot.yaml").write_text("snapshots:\n" + "\n".join(snaps) + "\n",
                                                                     encoding="utf-8")
            (tmp / "rules.yaml").write_text(rules, encoding="utf-8")
            (tmp / "licenses.json").write_text(json.dumps(licenses), encoding="utf-8")
            kw = dict(staging=staging, rules_path=tmp / "rules.yaml", licenses_path=tmp / "licenses.json",
                      check_registry=False, log=lambda *_: None)
            bundle_build.build(home, staging, rules_path=tmp / "rules.yaml", evidence=evidence,
                               licenses_path=tmp / "licenses.json", log=lambda *_: None)
            for name, sha in (("alpha", "b" * 40), ("beta", "c" * 40)):
                files = dict(FILES)
                files["skills/x/SKILL.md"] += f"{name} v2\n"
                src = tmp / f"src-{name}"
                for path, text in files.items():
                    (src / path).parent.mkdir(parents=True, exist_ok=True)
                    (src / path).write_text(text, encoding="utf-8")
                ev = home / "bundles" / "current" / "evidence"
                r = update(home, name, sha, source=src, evidence=ev if ev.is_dir() else evidence, **kw)
                self.assertEqual(r["status"], "activated", r.get("errors"))
            pins = (home / "bundles" / "current" / "evidence" / "upstream-staging-snapshot.yaml").read_text(encoding="utf-8")
            self.assertIn("b" * 40, pins)
            self.assertIn("c" * 40, pins)
