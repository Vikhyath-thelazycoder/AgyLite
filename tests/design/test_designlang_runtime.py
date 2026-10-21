"""MP4 §2.2: designlang is an isolated npm runtime with a lock — the audited version, installed without install
scripts, its Chromium inside the runtime folder, status like the other runtimes."""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.insert(0, ROOT_DIR)

from agylite.runtimes import designlang  # noqa: E402


class TestDesignlangRuntime(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_version_is_the_audited_pin(self):
        self.assertEqual(designlang.pinned_version(), "13.3.2")

    def test_install_is_pinned_scriptless_and_locked(self):
        calls = []

        def fake_run(argv, **kw):
            calls.append((argv, kw.get("env") or {}))
            d = Path(argv[argv.index("--prefix") + 1]) if "--prefix" in argv else None
            if d is not None:   # what npm would leave behind
                pkg = d / "node_modules" / "designlang"
                (pkg / "bin").mkdir(parents=True)
                (pkg / "package.json").write_text(json.dumps({"version": "13.3.2"}), encoding="utf-8")
                (d / "node_modules" / ".bin").mkdir(parents=True)
                (d / "node_modules" / ".bin" / "designlang").write_text("", encoding="utf-8")
                (d / "node_modules" / ".bin" / "playwright").write_text("", encoding="utf-8")
                (d / "package-lock.json").write_text(json.dumps({"packages": {"node_modules/designlang": {
                    "version": "13.3.2", "integrity": "sha512-abc"}}}), encoding="utf-8")
            else:
                (Path(kw["env"]["PLAYWRIGHT_BROWSERS_PATH"]) / "chromium-1").mkdir(parents=True)
            return mock.Mock(returncode=0, stdout="", stderr="")
        with mock.patch.object(designlang, "node_version", return_value=(22, 14, 0)), \
                mock.patch("shutil.which", return_value="/usr/bin/npm"), \
                mock.patch("subprocess.run", side_effect=fake_run):
            info = designlang.install(self.home, log=lambda *_: None)
        npm = calls[0][0]
        self.assertIn("--ignore-scripts", npm)
        self.assertIn("designlang@13.3.2", npm)
        self.assertTrue({"--no-audit", "--no-fund"} <= set(npm))
        rt = self.home / "runtimes" / "designlang-13.3.2"
        self.assertEqual(calls[1][1]["PLAYWRIGHT_BROWSERS_PATH"], str(rt / "browsers"))
        self.assertEqual(calls[1][0][-2:], ["install", "chromium"])
        lock = json.loads((rt / "lock.json").read_text())
        self.assertEqual((lock["version"], lock["integrity"]), ("13.3.2", "sha512-abc"))
        self.assertEqual(info["status"], "ready")
        h = designlang.health(self.home)
        self.assertEqual((h["status"], h["version"]), ("ready", "13.3.2"))
        self.assertEqual(designlang.runtime(self.home).env()["PLAYWRIGHT_BROWSERS_PATH"], str(rt / "browsers"))

    def test_status_before_install_and_old_node(self):
        self.assertEqual(designlang.health(self.home)["status"], "not-installed")
        with mock.patch.object(designlang, "node_version", return_value=(18, 0, 0)):
            with self.assertRaises(designlang.DesignlangError):
                designlang.install(self.home, log=lambda *_: None)


if __name__ == "__main__":
    unittest.main()
