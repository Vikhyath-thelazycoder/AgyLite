"""P13: lifecycle config, route lifecycle, domain adaptation transform (D-038), entry skills/agents, Unlazy runtime."""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.insert(0, ROOT_DIR)

from agylite.bundle.transforms import domain  # noqa: E402
from agylite.project.lifecycle import load_lifecycle, steps_for, validate_lifecycle  # noqa: E402
from agylite.routing import ProjectFacts, Router  # noqa: E402
from agylite.runtimes import unlazy  # noqa: E402

STAGED_UNLAZY = Path(ROOT_DIR) / ".staging" / "upstream" / "unlazy"


class TestLifecycle(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.router = Router()
        cls.cfg = load_lifecycle()

    def test_config_valid(self):
        types = [t["type"] for t in self.router.cfg["change_types"]["order"]]
        self.assertEqual(validate_lifecycle(self.cfg, types), [])
        self.assertIn("must end with RECONCILE", " ".join(validate_lifecycle(
            {**self.cfg, "change_types": {"default": {"steps": ["PLAN"]}}})))

    def test_bug_fix_tests_first(self):
        steps = steps_for(self.cfg, "BUG_FIX", "existing")
        self.assertEqual([s["step"] for s in steps], ["UNDERSTAND", "TEST", "IMPLEMENT", "VERIFY", "RECONCILE"])
        self.assertIn("failing regression test", steps[1]["rule"])
        self.assertIn("agylite codebase affected --paths <files>", steps[0]["commands"])

    def test_route_carries_lifecycle(self):
        r = self.router.route("build a SaaS for dentists", project=ProjectFacts(stage="new"))   # scenario A
        self.assertGreaterEqual(r["schema_version"], 4)
        self.assertEqual(r["lifecycle"][0]["commands"], ['agylite project questions "<request>"',
                                                         'agylite project answer <id> "<answer>"'])
        r = self.router.route("add Google Maps navigation to bookings", project=ProjectFacts(stage="existing"))
        self.assertEqual(r["lifecycle"][-1]["step"], "RECONCILE")
        self.assertIsNone(self.router.route("make a launch video plan for our product")["lifecycle"])


class TestDomainTransform(unittest.TestCase):
    def test_gstack_adaptation(self):
        text = ("---\nname: x\nhooks:\n  PreToolUse:\n    - matcher: Edit\ntriggers:\n  - a\n---\n"
                "<!-- agylite: gstack placeholder BASE_BRANCH_DETECT not recovered -->\n"
                "Read `~/.claude/skills/gstack/review/checklist.md`.\n"
                "Run gstack-review-read when done.\n"
                "```bash\ngit diff\n~/.claude/skills/gstack/bin/gstack-review-log --start \\\n  --x y\necho ok\n```\n")
        out, notes = domain.adapt("gstack", "review/SKILL.md", text, "engineering/review", {"review/checklist.md"})
        self.assertNotIn("hooks:", out)
        self.assertIn("triggers:", out)
        self.assertIn("## Step 0: Detect the base branch", out)
        self.assertIn("$AGYLITE_BUNDLE/files/gstack/review/checklist.md", out)
        self.assertIn("# [agylite] removed: gstack runtime step (gstack-review-log)", out)
        self.assertNotIn("--x y", out)          # continuation line removed with its command
        self.assertIn("git diff\n", out)
        self.assertIn("echo ok", out)
        self.assertIn("not part of Agylite — removed", out)
        self.assertIn("Agylite adaptation (D-038)", out)
        again, _ = domain.adapt("gstack", "review/SKILL.md", out, "engineering/review", {"review/checklist.md"})
        self.assertEqual(again, out)            # idempotent

    def test_browser_steps_stay_as_written(self):
        line = "For visual regression, use Playwright screenshots.\n"   # D-049: no "disabled" annotation any more
        out, notes = domain.adapt("ecc", "rules/react/testing.md", line, "engineering/stack-packs", set())
        self.assertEqual((out, notes), (line, []))
        out, notes = domain.adapt("brag", "SKILL.md", line, "media/launch-video", set())
        self.assertEqual((out, notes), (line, []))


class TestEntrySurfaces(unittest.TestCase):
    def test_workflows_retired(self):
        self.assertFalse(Path(ROOT_DIR, "workflows").exists())

    def test_agents_have_frontmatter(self):
        for f in Path(ROOT_DIR, "agents").glob("*.md"):
            head = f.read_text(encoding="utf-8").split("---")[1]
            self.assertIn(f"name: {f.stem}", head, f.name)
            self.assertIn("description:", head, f.name)

    def test_entry_skills_are_thin(self):
        for name in ("engineering", "security", "review", "production", "codebase"):
            text = Path(ROOT_DIR, "skills", f"agylite-{name}", "SKILL.md").read_text(encoding="utf-8")
            self.assertLessEqual(len(text.encode()), 2200, name)
            self.assertIn("agylite ", text)
            self.assertNotIn("ECC", text)       # no repo-first routing (MR-01)


@unittest.skipUnless(shutil.which("node") and STAGED_UNLAZY.is_dir(), "needs node and the staged unlazy upstream")
class TestUnlazyRuntime(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        self.home = base / "vh"
        (self.home / "bundles" / "b1" / "files").mkdir(parents=True)
        (self.home / "bundles" / "b1" / "files" / "unlazy").symlink_to(STAGED_UNLAZY)
        (self.home / "bundles" / "current").symlink_to("b1")
        self.user = base / "user"
        self.user.mkdir()
        self.project = base / "proj"
        self.project.mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def test_gates_lint_and_status(self):
        (self.project / "GATES.md").write_text(
            "# Gates\n\n- [ ] G1: marker exists\n  CHECK: node -e \"console.log('MARK_OK')\"\n  EXPECT: MARK_OK\n",
            encoding="utf-8")
        self.assertEqual(unlazy.gates(self.home, "lint", ["GATES.md"], self.project).returncode, 0)
        p = unlazy.gates(self.home, "status", ["GATES.md"], self.project)
        self.assertEqual(p.returncode, 1)      # unmet until approved and run
        self.assertIn("UNMET", p.stdout)

    def test_stop_hook_central_only(self):
        env = {**os.environ, "HOME": str(self.user)}
        old = os.environ.copy()
        os.environ.update(env)
        try:
            self.assertEqual(unlazy.stop_hook(self.home, enable=True).returncode, 0)
            settings = (self.user / ".claude" / "settings.json").read_text(encoding="utf-8")
            self.assertIn("bundles/current/files/unlazy/scripts/stop-hook.mjs", settings)
            self.assertFalse((self.project / ".claude").exists())
            self.assertEqual(unlazy.stop_hook(self.home, enable=False).returncode, 0)
            self.assertNotIn("stop-hook.mjs", (self.user / ".claude" / "settings.json").read_text(encoding="utf-8"))
        finally:
            os.environ.clear()
            os.environ.update(old)


if __name__ == "__main__":
    unittest.main()
