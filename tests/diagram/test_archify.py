"""MP5 §3.4 + owner approval 2026-10-22: `agylite diagram` runs the bundled Archify CLI in the project with the exit code
kept, Archify's update check off and credentials stripped; the Chrome browser-check runs whenever Chrome is present
(explainers get --browser-check) and, without Chrome, finalize runs validate → deliver → check and says the browser
check was skipped; verify re-runs check + browser-check on delivered diagrams (the one scoped browser gate)."""
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

from agylite.bundle.transforms import rewrites  # noqa: E402
from agylite.runtimes import archify  # noqa: E402
from agylite.verify import diagram, run as vrun  # noqa: E402

UPSTREAM = Path.home() / "Developer" / "os" / "archify" / "archify"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"


def fake_bundle(base: Path) -> Path:
    cli = base / "bundle" / archify.CLI
    cli.parent.mkdir(parents=True)
    cli.write_text("// stub\n", encoding="utf-8")
    return base / "bundle"


class TestPlan(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.bundle = fake_bundle(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def test_passthrough(self):
        [argv] = archify.plan(self.bundle, ["guide", "login flow", "--json"], CHROME)
        self.assertEqual(Path(argv[1]), self.bundle / archify.CLI)
        self.assertEqual(argv[2:], ["guide", "login flow", "--json"])

    def test_finalize_with_chrome_runs_archify_finalize(self):
        [argv] = archify.plan(self.bundle, ["finalize", "sequence", "c.json", "o.html", "--json"], CHROME)
        self.assertEqual(argv[2:], ["finalize", "sequence", "c.json", "o.html", "--json"])   # native: always checks
        [argv] = archify.plan(self.bundle, ["finalize", "explainer", "c.md", "o.html"], CHROME)
        self.assertIn("--browser-check", argv)   # required whenever Chrome is present

    def test_finalize_without_chrome_runs_the_other_gates(self):
        steps = archify.plan(self.bundle, ["finalize", "erd", "c.json", "o.html", "--quality", "standard",
                                           "--repo-root", ".", "--json"], None)
        self.assertEqual([s[2] for s in steps], ["validate", "deliver", "check"])
        self.assertEqual(steps[0][3:], ["erd", "c.json", "--quality", "standard", "--repo-root", ".", "--json"])
        self.assertEqual(steps[2][3:], ["o.html", "--require-provenance", "--json"])
        self.assertTrue(all("--browser-check" not in s for s in steps))

    def test_bad_finalize_and_missing_bundle(self):
        with self.assertRaises(archify.ArchifyError):
            archify.plan(self.bundle, ["finalize", "poster", "c.json", "o.html"], CHROME)
        with self.assertRaises(archify.ArchifyError):
            archify.plan(None, ["guide"], CHROME)

    def test_env_disables_update_check_and_strips_secrets(self):
        with mock.patch.dict(os.environ, {"OPENAI_API_KEY": "sk-x", "GH_TOKEN": "t", "HOME": "/h"}):
            env = archify.env_for(CHROME)
        self.assertEqual(env["ARCHIFY_UPDATE_CHECK_DISABLED"], "1")
        self.assertEqual(env["ARCHIFY_CHROME"], CHROME)
        self.assertNotIn("OPENAI_API_KEY", env)
        self.assertNotIn("GH_TOKEN", env)
        self.assertNotIn("ARCHIFY_CHROME", archify.env_for(None))

    def test_chrome_discovery_honours_archify_chrome(self):
        self.assertIsNone(archify.find_chrome({"ARCHIFY_CHROME": ""}))
        self.assertEqual(archify.find_chrome({"ARCHIFY_CHROME": sys.executable}), sys.executable)

    def test_run_keeps_exit_code_and_stops_at_first_failure(self):
        calls = []

        def fake(argv, **kw):
            calls.append(argv[2])
            return subprocess.CompletedProcess(argv, 3 if argv[2] == "deliver" else 0, "", "")
        logs = []
        with mock.patch.object(archify, "find_chrome", return_value=None), mock.patch("subprocess.run", fake):
            p, info = archify.run(self.bundle, ["finalize", "tree", "c.json", "o.html"], cwd=Path("."), log=logs.append)
        self.assertEqual((p.returncode, calls), (3, ["validate", "deliver"]))
        self.assertEqual(info["browser_check"], "skipped")
        self.assertIn("browser-check skipped", logs[0])


class TestVerifyGate(unittest.TestCase):
    def test_only_the_diagram_gate_may_name_a_browser(self):
        gate = [sys.executable, "-m", "agylite.cli", "diagram", "--project", "/p", "browser-check", "/p/x.html", "--json"]
        self.assertTrue(vrun.scoped_gate(gate))
        self.assertTrue(vrun.scoped_gate([sys.executable, "-m", "agylite.cli", "diagram", "check", "x.html"]))
        self.assertFalse(vrun.scoped_gate([sys.executable, "-m", "agylite.cli", "diagram", "preview", "x"]))
        self.assertFalse(vrun.scoped_gate(["npx", "chrome-devtools", "screenshot"]))
        with self.assertRaises(ValueError):
            vrun.run_check(["npx", "chrome-devtools", "screenshot"], ".")

    def test_changed_archify_folders_and_named_pages(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            folder = root / ".archify" / "sequence-login-20261022-120000"
            folder.mkdir(parents=True)
            (folder / "login.html").write_text("<html></html>", encoding="utf-8")
            (folder / "candidate.json").write_text("{}", encoding="utf-8")
            other = root / "docs" / "x.html"
            other.parent.mkdir()
            other.write_text("<html></html>", encoding="utf-8")
            self.assertEqual(diagram.outputs(root, [".archify/sequence-login-20261022-120000/candidate.json"]),
                             [folder / "login.html"])
            self.assertEqual(diagram.outputs(root, ["src/app.py"], ["docs/x.html"]), [other])
            self.assertEqual(diagram.outputs(root, ["src/app.py"]), [])

            class P:
                pass
            project = P()
            project.root = root
            with mock.patch.object(archify, "find_chrome", return_value=None):
                chk = diagram.checks(project, [".archify/sequence-login-20261022-120000/login.html"])
            self.assertEqual([c.name for c, *_ in chk], ["archify check", "archify browser-check"])
            self.assertIsNone(chk[1][1])                       # NOT_RUN → BLOCKED, never a pass
            self.assertIn("chrome missing", chk[1][0].notes[0])
            with mock.patch.object(archify, "find_chrome", return_value=CHROME):
                chk = diagram.checks(project, [".archify/sequence-login-20261022-120000/login.html"])
            self.assertIn("browser-check", chk[1][1])


@unittest.skipUnless((UPSTREAM / "SKILL.md").is_file(), "archify upstream clone not present")
class TestUpstream(unittest.TestCase):
    def test_rewrites_match_and_remove_proactive_and_update(self):
        out = rewrites.apply("archify", "archify/SKILL.md", (UPSTREAM / "SKILL.md").read_text(encoding="utf-8"))
        for gone in ("bin/archify.mjs` in every", "node bin/archify.mjs", "[archify explainer: proactive]",
                     "always-on", "noticeRequired", "update-awareness.md", "mode offer"):
            self.assertNotIn(gone, out)
        self.assertIn("agylite diagram finalize <type> <candidate.json> <output.html>", out)
        self.assertIn("Explainer pages are made only when the user asks for one", out)
        self.assertIn("Agylite manages Archify updates; ignore update notices in receipts.", out)
        self.assertIn("## Type router", out)                  # method, schemas and repair contract stay
        self.assertIn("repair the failed gate", out)

    @unittest.skipUnless(shutil.which("node"), "node not installed")
    def test_every_example_validates_without_a_browser(self):
        with tempfile.TemporaryDirectory() as tmp:
            bundle = Path(tmp) / "bundle"
            shutil.copytree(UPSTREAM, bundle / "files" / "archify" / "archify",
                            ignore=lambda d, names: [n for n in names if d.endswith("examples") and n.endswith(".html")])
            r = archify.self_test(bundle)
        self.assertTrue(r["ok"], r)
        self.assertGreaterEqual(len(r["exit_codes"]), 10)


if __name__ == "__main__":
    unittest.main()
