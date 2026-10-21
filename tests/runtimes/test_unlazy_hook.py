"""MP3 §3.2: the installer enables Unlazy's Stop hook through the one existing writer (`agylite runtime unlazy-hook`),
idempotently, reports what changed in ~/.claude/settings.json, and `--disable` removes only Agylite's entry."""
import contextlib
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.insert(0, ROOT_DIR)

from agylite.cli import main  # noqa: E402
from agylite.runtimes import unlazy  # noqa: E402

REAL = Path.home() / ".agylite" / "bundles" / "current" / "files" / "unlazy" / "scripts"
OTHER = {"matcher": "", "hooks": [{"type": "command", "command": "/usr/local/bin/my-own-stop-hook"}]}


@unittest.skipUnless(shutil.which("node") and (REAL / "install-hooks.mjs").is_file(),
                     "node and an installed bundle with Unlazy's scripts are needed")
class TestUnlazyStopHook(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        self.user, self.ahome = base / "user", base / "agylite"
        scripts = self.ahome / "bundles" / "b1" / "files" / "unlazy"
        scripts.mkdir(parents=True)
        shutil.copytree(REAL, scripts / "scripts")
        (self.ahome / "bundles" / "current").symlink_to("b1")
        self.settings = self.user / ".claude" / "settings.json"
        self.settings.parent.mkdir(parents=True)
        self.settings.write_text(json.dumps({"hooks": {"Stop": [OTHER]}, "theme": "dark"}), encoding="utf-8")
        self.env = mock.patch.dict(os.environ, {"HOME": str(self.user), "AGYLITE_HOME": str(self.ahome)})
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.tmp.cleanup()

    def run_cli(self, *argv):
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            code = main(list(argv))
        return code, out.getvalue()

    def stop_groups(self):
        return json.loads(self.settings.read_text(encoding="utf-8"))["hooks"].get("Stop", [])

    def test_enable_twice_one_entry_disable_keeps_other_hooks(self):
        code, out = self.run_cli("runtime", "unlazy-hook", "--enable")
        self.assertEqual(code, 0, out)
        self.assertIn("~/.claude/settings.json: added Stop hook", out)
        self.assertEqual(unlazy.stop_hook_state(self.settings), "enabled")
        code, out = self.run_cli("runtime", "unlazy-hook", "--enable")
        self.assertEqual(code, 0, out)
        self.assertIn("~/.claude/settings.json: unchanged", out)
        cmds = [h["command"] for g in self.stop_groups() for h in g["hooks"]]
        self.assertEqual(sum("stop-hook.mjs" in c for c in cmds), 1)
        self.assertIn(OTHER["hooks"][0]["command"], cmds)
        code, out = self.run_cli("runtime", "unlazy-hook", "--disable")
        self.assertEqual(code, 0, out)
        self.assertIn("~/.claude/settings.json: removed Stop hook", out)
        self.assertEqual(self.stop_groups(), [OTHER])
        self.assertEqual(json.loads(self.settings.read_text(encoding="utf-8"))["theme"], "dark")
        self.assertEqual(unlazy.stop_hook_state(self.settings), "disabled")


class TestInstallerAndDoctor(unittest.TestCase):
    def test_installer_enables_the_hook_with_the_one_writer(self):
        text = (Path(ROOT_DIR) / "scripts" / "install").read_text(encoding="utf-8")
        self.assertIn('"$HOME_DIR/core/bin/agylite" runtime unlazy-hook --enable', text)
        self.assertLess(text.index("bundle verify"), text.index("unlazy-hook --enable"))

    def test_doctor_reports_the_hook(self):
        from agylite.diagnostics import doctor
        seen = []

        class R:
            def check(self, ok, good, bad):
                seen.append(good if ok else bad)

            def warn(self, msg):
                seen.append(msg)
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.dict(os.environ, {"HOME": tmp}):
                doctor.unlazy_hook_checks(R())
        self.assertTrue(any(s.startswith("Unlazy Stop hook: disabled") for s in seen), seen)


if __name__ == "__main__":
    unittest.main()
