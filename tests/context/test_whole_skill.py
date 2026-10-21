"""IMPLEMENTATION_PLAN §2.1 (Plan B): a routed capability's primary skill loads whole — every section, no truncation —
its own files are listed for on-demand reading, and `agylite skill load <repo>/<name>` prints one whole skill."""
import contextlib
import io
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.insert(0, ROOT_DIR)

from tests.context.fixtures import FILES, make_bundle, make_project  # noqa: E402
from agylite.cli import main  # noqa: E402
from agylite.context import levels  # noqa: E402
from agylite.context.budget import load_budgets  # noqa: E402
from agylite.context.loader import ContextLoader  # noqa: E402
from agylite.context.sections import split_sections  # noqa: E402
from agylite.project.identity import detect  # noqa: E402

PRIMARY = "files/alpha/skills/security-review/SKILL.md"


class Env(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        self.home = base / "home"
        self.bundle = make_bundle(self.home)
        self.root = make_project(base)
        self.env = mock.patch.dict(os.environ, {"AGYLITE_HOME": str(self.home)})
        self.env.start()
        self.project = detect(self.root, home=self.home)
        self.budgets = load_budgets()

    def tearDown(self):
        self.env.stop()
        self.tmp.cleanup()

    def loader(self, session=None):
        return ContextLoader(self.project, session, self.bundle, home=self.home)


class TestWholeSkill(Env):
    def test_budget_config_is_plan_b(self):
        l2 = self.budgets["levels"]["L2"]
        self.assertEqual((l2["primary_skill"], l2["max_whole_skills_per_task"], l2["max_tokens_per_task"]),
                         ("whole", 2, 40000))
        self.assertNotIn("max_files_per_capability", l2)
        self.assertIn("IMPLEMENTATION_PLAN", l2["why"])

    def test_primary_skill_loads_whole_with_zero_truncation(self):
        caps = ["engineering/security", "engineering/backend", "testing/security"]
        l2 = levels.capability_context(self.loader(), caps, self.budgets, query="webhook signature",
                                       priorities={"engineering/security": [PRIMARY]})
        text = FILES[PRIMARY]
        for s in split_sections(text):
            self.assertIn(s.title, l2["text"])                 # every section, not a slice
        self.assertIn(text.strip()[-40:], l2["text"])          # through the very end
        self.assertNotIn("(sections ", l2["text"])
        self.assertNotIn("More sections:", l2["text"])
        self.assertEqual(l2["capabilities_full"], ["engineering/security"])
        self.assertEqual(l2["capabilities_index_only"], ["engineering/backend", "testing/security"])
        self.assertIn("agylite skill load beta/test-security", l2["text"])     # index-only names its skill

    def test_skill_files_are_listed_not_loaded(self):
        prio = {"engineering/security": ["files/alpha/skills/hardening/SKILL.md"]}
        loader = self.loader()
        l2 = levels.capability_context(loader, ["engineering/security"], self.budgets, priorities=prio)
        self.assertIn("files/alpha/skills/hardening/references/checklist.md", l2["text"])
        self.assertNotIn("## Auth", l2["text"])                # the reference itself is not loaded
        self.assertEqual([e["path"] for e in loader.log], ["files/alpha/skills/hardening/SKILL.md"])

    def test_two_whole_skills_when_asked(self):
        l2 = levels.capability_context(self.loader(), ["engineering/security", "testing/security"], self.budgets,
                                       priorities={"engineering/security": [PRIMARY]}, whole=2)
        self.assertEqual(l2["capabilities_full"], ["engineering/security", "testing/security"])
        self.assertIn(FILES["files/beta/skills/test-security/SKILL.md"].strip()[-40:], l2["text"])

    def test_primary_may_be_another_capabilitys_skill(self):
        """MP4 §1.5: a capability's sources_priority may name a skill bundled under another capability; it loads whole
        as this capability's primary (the file is bundled once)."""
        other = "files/beta/skills/test-security/SKILL.md"
        l2 = levels.capability_context(self.loader(), ["engineering/backend"], self.budgets,
                                       priorities={"engineering/backend": [other]})
        self.assertIn(f"### {other}", l2["text"])
        self.assertIn(FILES[other].strip()[-40:], l2["text"])

    def test_second_session_load_is_a_cache_marker(self):
        args = (["engineering/security"], self.budgets)
        kw = {"priorities": {"engineering/security": [PRIMARY]}}
        first = self.loader("s1")
        levels.capability_context(first, *args, **kw)
        first.finish()                                          # the session cache is saved when a load finishes
        again = levels.capability_context(self.loader("s1"), *args, **kw)["text"]
        self.assertIn("[cached] " + PRIMARY, again)


class TestSkillLoadCommand(Env):
    def run_cli(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = main(list(argv))
        return code, out.getvalue(), err.getvalue()

    def test_load_prints_the_whole_skill_and_its_files(self):
        code, out, _ = self.run_cli("skill", "load", "alpha/hardening", "--project", str(self.root))
        self.assertEqual(code, 0)
        self.assertIn(FILES["files/alpha/skills/hardening/SKILL.md"].strip()[-40:], out)
        self.assertIn("files/alpha/skills/hardening/references/checklist.md", out)
        self.assertIn(str(self.bundle / "files/alpha/skills/hardening"), out)   # the folder relative links use

    def test_unknown_skill_suggests_search(self):
        code, _, err = self.run_cli("skill", "load", "alpha/nope", "--project", str(self.root))
        self.assertEqual(code, 2)
        self.assertIn("agylite skills search", err)


if __name__ == "__main__":
    unittest.main()
