"""MP4 §1.3–1.4: Taste v2.1's scripts run as the `agylite design taste` runtime — scripts from the bundle, run in the
project, TASTE_SKILL_TMP and the draw memory under the Agylite home, node >= 22 and a browser reported by status."""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.insert(0, ROOT_DIR)

from agylite.runtimes import taste  # noqa: E402

UPSTREAM = Path.home() / "Developer" / "os" / "taste-skill" / "skills" / "taste-skill" / "scripts"
FIXTURES = Path(ROOT_DIR) / "tests" / "fixtures" / "taste"


def fake_bundle(base: Path) -> Path:
    scripts = base / "bundle" / "files" / "taste" / "skills" / "taste-skill" / "scripts"
    scripts.mkdir(parents=True)
    for name in taste.SCRIPTS:
        (scripts / f"{name}.mjs").write_text("// stub\n", encoding="utf-8")
    return base / "bundle"


class TestTasteRuntime(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.bundle, self.home = fake_bundle(self.base), self.base / "home"

    def tearDown(self):
        self.tmp.cleanup()

    def test_status_reports_missing_node_and_browser(self):
        with mock.patch("shutil.which", return_value=None), mock.patch.object(taste, "MAC_BROWSERS", ()), \
                mock.patch.dict(os.environ, {"CHROME_PATH": ""}):
            h = taste.health(self.bundle, self.home)
        self.assertEqual((h["status"], h["node"], h["browser"]), ("broken", "missing: node>=22", "missing"))
        with mock.patch.object(taste, "node_version", return_value=(20, 11, 0)):
            self.assertEqual(taste.health(self.bundle, self.home)["node"], "missing: node>=22 (found 20.11.0)")
        self.assertEqual(taste.health(None, self.home)["status"], "no-bundle")

    def test_commands_run_bundle_scripts_with_agylite_paths(self):
        argv, env = taste.command(self.bundle, self.home, "inspect", ["index.html", "--app"])
        self.assertEqual(argv[1:], [str(self.bundle / taste.SKILL_SCRIPTS / "inspect.mjs"), "index.html", "--app"])
        self.assertEqual(env["TASTE_SKILL_TMP"], str(self.home / "tmp" / "taste"))
        self.assertEqual(env["TASTE_SKILL_HISTORY"], str(self.home / "taste" / "history.json"))
        self.assertTrue((self.home / "tmp" / "taste").is_dir())
        for name in ("draw", "lint", "scenes", "assets"):
            self.assertTrue(taste.command(self.bundle, self.home, name, [])[0][1].endswith(f"/{name}.mjs"))
        with self.assertRaises(taste.TasteError):
            taste.command(self.bundle, self.home, "evil", [])

    def test_key_env_vars_never_reach_the_scripts(self):
        with mock.patch.dict(os.environ, {"OPENAI_API_KEY": "x", "ANTHROPIC_API_KEY": "y", "GITHUB_TOKEN": "z"}):
            _, env = taste.command(self.bundle, self.home, "assets", ["harbour"])
        self.assertFalse({"OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GITHUB_TOKEN"} & set(env))


@unittest.skipUnless(shutil.which("node") and (taste.node_version() or (0,))[0] >= 22 and UPSTREAM.is_dir(),
                     "node >= 22 and the taste-skill clone are needed")
class TestTasteLintFixtures(unittest.TestCase):
    """§1.4 self-test: lint exits 0 on a clean page and 1 on a page with known tells."""

    def test_lint_fixture_exit_codes(self):
        with tempfile.TemporaryDirectory() as tmp:
            bundle = Path(tmp) / "bundle"
            shutil.copytree(UPSTREAM, bundle / taste.SKILL_SCRIPTS)
            results = taste.self_test(bundle, Path(tmp) / "home", FIXTURES)
        self.assertEqual(results["exit_codes"], {"clean.html": 0, "tell.html": 1})
        self.assertTrue(results["ok"])


if __name__ == "__main__":
    unittest.main()
