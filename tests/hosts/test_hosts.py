"""P19–P22 (D-042): adapters are packaging only; every host gets the same policy; status levels are honest (§34)."""
import ast
import contextlib
import io
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

from agylite.adapters import ADAPTERS, all_adapters, get, record_runtime  # noqa: E402
from agylite.adapters.base import entry_skills  # noqa: E402
from agylite.cli import main  # noqa: E402

FORBIDDEN = ("mcpServers", "mcp_config", "chrome-devtools", "take_screenshot", "playwright", "\"PreToolUse\"",
             "\"UserPromptSubmit\"")


class TestNoLogic(unittest.TestCase):
    def test_adapters_import_no_routing_state_or_context(self):
        for f in Path(ROOT_DIR, "agylite", "adapters").glob("*.py"):
            tree = ast.parse(f.read_text(encoding="utf-8"))
            mods = {n.module or "" for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)}
            mods |= {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
            for bad in ("routing", "project", "context", "registry", "verify", "codebase"):
                self.assertFalse(any(bad in m for m in mods), f"{f.name} imports {bad}")


class TestPolicy(unittest.TestCase):
    def test_repo_files_current(self):
        self.assertEqual({a.host: a.stale() for a in all_adapters() if a.stale()}, {})

    def test_every_host_gets_the_same_policy_and_no_mcp_or_browser(self):
        skills = entry_skills()
        self.assertGreaterEqual(len(skills), 10)
        for name, text in skills.items():
            self.assertIn("config/verification.yaml", text, name)
        for a in all_adapters():
            for rel, text in a.repo_files().items():
                for word in FORBIDDEN:
                    self.assertNotIn(word, text, f"{a.host} {rel}")
        self.assertIn("config/verification.yaml", get("antigravity").repo_files()[".agents/skills/agylite/SKILL.md"])

    def test_claude_hooks_only_session_bootstrap(self):
        hooks = json.loads(Path(ROOT_DIR, "hooks", "hooks.json").read_text(encoding="utf-8"))["hooks"]
        self.assertEqual(list(hooks), ["SessionStart"])
        cmd = hooks["SessionStart"][0]["hooks"][0]["command"]
        self.assertIn("${CLAUDE_PLUGIN_ROOT}/bin/agylite", cmd)
        self.assertIn("bootstrap --host claude-code", cmd)

    def test_manifest_versions_match(self):
        version = Path(ROOT_DIR, "VERSION").read_text(encoding="utf-8").strip()
        for rel in (".claude-plugin/plugin.json", ".codex-plugin/plugin.json"):
            self.assertEqual(json.loads(Path(ROOT_DIR, rel).read_text(encoding="utf-8"))["version"], version)
        self.assertEqual(json.loads(Path(ROOT_DIR, ".codex-plugin/plugin.json").read_text(encoding="utf-8"))["skills"],
                         "./skills/")


class TestStatusAndInstall(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        self.user, self.home = base / "user", base / "vh"
        self.user.mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def test_levels_are_separate(self):
        a = get("cursor", home=self.home, user_home=self.user)
        self.assertEqual(a.status()["status"], "FILES_PRESENT")
        written = a.install()
        self.assertEqual(len(written), len(entry_skills()))
        self.assertTrue((self.user / ".cursor" / "skills" / "agylite-routing" / "SKILL.md").is_file())
        self.assertEqual(a.status()["status"], "INSTALLED")          # installed is not runtime-verified
        record_runtime("cursor", "p1", home=self.home)
        self.assertEqual(a.status()["status"], "RUNTIME_VERIFIED")
        self.assertEqual(len(a.uninstall()), len(written))
        self.assertFalse(list((self.user / ".cursor" / "skills").glob("agylite-*")))

    def test_install_never_overwrites_foreign_skill(self):
        foreign = self.user / ".gemini" / "config" / "skills" / "agylite-routing"
        foreign.mkdir(parents=True)
        (foreign / "SKILL.md").write_text("mine", encoding="utf-8")
        with self.assertRaises(FileExistsError):
            get("antigravity", home=self.home, user_home=self.user).install()
        self.assertEqual((foreign / "SKILL.md").read_text(encoding="utf-8"), "mine")

    def test_plugin_hosts_report_their_installer(self):
        for host in ("claude-code", "codex"):
            st = get(host, home=self.home, user_home=self.user).status()
            self.assertFalse(st["installed"])
            self.assertIn("plugin", st["how"])
        reg = self.user / ".claude" / "plugins"
        reg.mkdir(parents=True)
        (reg / "installed_plugins.json").write_text(json.dumps({"version": 2, "plugins": {
            "agylite@agylite-marketplace": [{"version": "1.0.1"}]}}), encoding="utf-8")
        st = get("claude-code", home=self.home, user_home=self.user).status()
        self.assertEqual((st["status"], st["version"]), ("INSTALLED", "1.0.1"))

    def test_launcher_bootstrap_records_runtime(self):
        (self.home / "bundles" / "b1").mkdir(parents=True)          # the source fallback needs a built bundle
        (self.home / "bundles" / "current").symlink_to("b1")
        env = {**os.environ, "AGYLITE_HOME": str(self.home), "HOME": str(self.user),
               "AGYLITE_PYTHON": sys.executable, "PATH": f"{Path(sys.executable).parent}:/usr/bin:/bin"}
        p = subprocess.run([str(Path(ROOT_DIR, "bin", "agylite")), "bootstrap", "--host", "claude-code"],
                           cwd=ROOT_DIR, env=env, capture_output=True, text=True, timeout=60)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("L0 bootstrap", p.stdout)
        self.assertIn("cli: ", p.stdout)
        rec = json.loads((self.home / "hosts" / "claude-code.json").read_text(encoding="utf-8"))
        self.assertEqual(rec["bootstraps"], 1)

    def test_launcher_refreshes_an_older_engine_at_session_start(self):
        import shutil
        import stat
        import time
        plugin = self.home.parent / "plugin"
        (plugin / "bin").mkdir(parents=True)
        (plugin / "scripts").mkdir()
        shutil.copy(Path(ROOT_DIR, "bin", "agylite"), plugin / "bin" / "agylite")
        marker = self.home.parent / "installed"
        (plugin / "scripts" / "install").write_text(f"#!/bin/sh\ntouch '{marker}'\n", encoding="utf-8")
        engine = self.home / "core" / "bin"
        engine.mkdir(parents=True)
        (engine / "agylite").write_text("#!/bin/sh\necho engine-ran\n", encoding="utf-8")
        (self.home / "src").mkdir()
        for f in (plugin / "bin" / "agylite", plugin / "scripts" / "install", engine / "agylite"):
            f.chmod(f.stat().st_mode | stat.S_IEXEC)
        env = {**os.environ, "AGYLITE_HOME": str(self.home), "HOME": str(self.user)}
        env.pop("AGYLITE_NO_AUTO_UPDATE", None)

        def start(plugin_version, engine_version, **extra):
            (plugin / "VERSION").write_text(plugin_version, encoding="utf-8")
            (self.home / "src" / "VERSION").write_text(engine_version, encoding="utf-8")
            marker.unlink(missing_ok=True)
            p = subprocess.run([str(plugin / "bin" / "agylite"), "bootstrap"], env={**env, **extra},
                               capture_output=True, text=True, timeout=30)
            for _ in range(50):            # the refresh runs in the background
                if marker.exists() or not (self.home / ".updating").exists():
                    break
                time.sleep(0.1)
            return p.stdout

        out = start("2.1.10", "2.1.9")
        self.assertIn("updating in the background: 2.1.9 → 2.1.10", out)
        self.assertIn("engine-ran", out)                    # the session itself is never held up
        for _ in range(50):
            if marker.exists():
                break
            time.sleep(0.1)
        self.assertTrue(marker.exists())
        self.assertNotIn("updating", start("2.1.5", "2.1.5"))                               # same version
        self.assertNotIn("updating", start("2.1.4", "2.1.5"))                               # never a downgrade
        self.assertNotIn("updating", start("2.2.0", "2.1.5", AGYLITE_NO_AUTO_UPDATE="1"))   # opted out
        self.assertFalse(marker.exists())

    def test_cli(self):
        out = io.StringIO()
        with mock.patch.dict(os.environ, {"AGYLITE_HOME": str(self.home)}), contextlib.redirect_stdout(out):
            self.assertEqual(main(["adapters", "render", "--check"]), 0)
            self.assertEqual(main(["adapters", "status", "--json"]), 0)
        self.assertEqual(len(json.loads(out.getvalue().split("\n", 1)[1])["hosts"]), len(ADAPTERS))


if __name__ == "__main__":
    unittest.main()
