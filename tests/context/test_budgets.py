"""P9: budgets config, sectioning, L0–L3 assembly limits, explicit-only L3, project identity."""
import contextlib
import copy
import io
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.insert(0, ROOT_DIR)

from tests.context.fixtures import make_bundle, make_project  # noqa: E402
from agylite.cli import main  # noqa: E402
from agylite.context import levels  # noqa: E402
from agylite.context.budget import load_budgets, validate_budgets  # noqa: E402
from agylite.context.loader import ContextError, ContextLoader, file_kind  # noqa: E402
from agylite.context.sections import pick_sections, split_sections  # noqa: E402
from agylite.project.identity import ProjectRef, compute_id, current_branch, detect, normalize_origin  # noqa: E402


class TestBudgetsConfig(unittest.TestCase):
    def test_valid_and_documented(self):
        cfg = load_budgets()
        self.assertEqual(validate_budgets(cfg), [])
        self.assertEqual(cfg["levels"]["L0"]["max_tokens"], 1500)   # D-014 starting values
        self.assertEqual(cfg["levels"]["L2"]["max_tokens_per_task"], 40000)   # Plan B (IMPLEMENTATION_PLAN §2.1)

    def test_planted_errors(self):
        cfg = copy.deepcopy(load_budgets())
        cfg["levels"]["L3"]["explicit_only"] = False
        del cfg["levels"]["L1"]["why"]
        cfg["code_files_per_task"]["value"] = 0
        problems = " | ".join(validate_budgets(cfg))
        for needle in ("explicit_only", "L1: missing `why`", "code_files_per_task"):
            self.assertIn(needle, problems)


class TestSections(unittest.TestCase):
    TEXT = "---\nname: x\n---\nintro\n# A\na\n## B\nb\n```\n# fenced\n```\n## B\nb2\n"

    def test_split(self):
        secs = split_sections(self.TEXT)
        self.assertEqual([s.id for s in secs], ["intro", "a", "b", "b-2"])
        self.assertEqual(self.TEXT[secs[2].start:secs[2].end], "## B\nb\n```\n# fenced\n```\n")

    def test_pick_with_budget_query_and_wanted(self):
        secs = split_sections(self.TEXT)
        chosen, skipped, truncated = pick_sections(secs, 1000)
        self.assertEqual((len(chosen), skipped, truncated), (4, [], False))
        chosen, _, _ = pick_sections(secs, 1000, wanted=["b-2"])
        self.assertEqual([s.id for s in chosen], ["b-2"])
        self.assertEqual(pick_sections(secs, 1000, wanted=["missing"])[0], [])
        _, _, truncated = pick_sections(secs, 1)
        self.assertTrue(truncated)


class Env(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        self.home = base / "home"
        self.bundle = make_bundle(self.home)
        self.root = make_project(base)
        self.project = detect(self.root, home=self.home)
        self.budgets = load_budgets()
        self.env = mock.patch.dict(os.environ, {"AGYLITE_HOME": str(self.home)})
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.tmp.cleanup()

    def loader(self, session=None, **kw):
        return ContextLoader(self.project, session, self.bundle, **kw)


class TestLevels(Env):
    def test_l0_within_budget_and_truncates_state(self):
        l0 = levels.bootstrap(project=self.project, session_id="s", host="cli", bundle_dir=self.bundle,
                              budgets=self.budgets)
        self.assertLessEqual(l0["est_tokens"], 1500)
        for needle in ("project: proj", "session: s", "branch main", "seo: runtime", "bundle fixturebundle"):
            self.assertIn(needle, l0["text"])
        flood = [f"line {i} " + "x" * 200 for i in range(100)]
        l0 = levels.bootstrap(project=self.project, session_id="s", host="cli", bundle_dir=self.bundle,
                              budgets=self.budgets, state_lines=flood)
        self.assertLessEqual(l0["est_tokens"], 1500)
        self.assertIn("truncated to the L0 budget", l0["text"])

    def test_l1_routed_cards_and_domain_budget(self):
        loader = self.loader()
        l1 = levels.domain_context(loader, ["engineering/security", "testing/security"], self.budgets)
        self.assertIn("# engineering/security", l1["text"])
        self.assertEqual(len(loader.log), 2)
        tiny = copy.deepcopy(self.budgets)
        tiny["levels"]["L1"]["max_tokens_per_domain"] = 200
        l1 = levels.domain_context(self.loader(), ["engineering/security", "engineering/backend"], tiny)
        self.assertIn("L1 budget reached for engineering; more cards: engineering/backend", l1["text"])

    def test_l2_whole_primary_skill_and_index_only(self):
        """Plan B (IMPLEMENTATION_PLAN §2.1) replaced section-picked slices of two files per capability: the first
        capability's primary skill loads whole, the others are index only; references are listed, never loaded."""
        loader = self.loader()
        caps = ["engineering/security", "engineering/backend", "testing/security", "codebase/impact-analysis"]
        l2 = levels.capability_context(loader, caps, self.budgets, query="webhook signature",
                                       priorities={"engineering/security": ["files/alpha/skills/security-review/SKILL.md"]})
        self.assertLessEqual(l2["est_tokens"], self.budgets["levels"]["L2"]["max_tokens_per_task"])
        self.assertEqual(l2["capabilities_full"], ["engineering/security"])
        self.assertEqual(l2["capabilities_index_only"], caps[1:])
        kinds = {file_kind(e["path"]) for e in loader.log}
        self.assertEqual(kinds, {"skill"}, "L2 loads the whole primary skill only; references stay on demand")
        self.assertIn("## Webhook signature verification", l2["text"])
        self.assertIn("## Dependency audit", l2["text"])                                # the last section too
        self.assertNotIn("More sections:", l2["text"])

    def test_l3_explicit_file_and_sections(self):
        loader = self.loader()
        l3 = levels.deep_reference(loader, "files/alpha/skills/hardening/references/checklist.md", self.budgets,
                                   sections=["input"])
        self.assertIn("## Input", l3["text"])
        self.assertNotIn("## Auth", l3["text"])
        with self.assertRaises(ContextError):
            levels.deep_reference(loader, "files/alpha/LICENSE", self.budgets)
        with self.assertRaises(ContextError):
            levels.deep_reference(loader, "../../etc/passwd", self.budgets)

    def test_cli_l3_only_with_file(self):
        err = io.StringIO()
        with contextlib.redirect_stderr(err), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main(["context", "engineering/security", "--level", "3", "--project", str(self.root)]), 2)
        self.assertIn("explicit only", err.getvalue())
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(main(["context", "--file", "files/alpha/scripts/check.sh", "--project", str(self.root)]), 0)
        self.assertIn("echo ok", out.getvalue())

    def test_cli_route_then_context(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(main(["context", "--route", "Fix the payment webhook security.", "--project",
                                   str(self.root)]), 0)
        self.assertIn("## engineering/security · L2", out.getvalue())
        self.assertIn("levels L1, L2", out.getvalue())


class TestIdentity(unittest.TestCase):
    def test_normalize_origin(self):
        for raw in ("git@github.com:Example/Proj.git", "https://github.com/Example/Proj",
                    "ssh://git@GitHub.com:22/Example/Proj.git", "https://user:token@github.com/Example/Proj.git/"):
            self.assertEqual(normalize_origin(raw), "github.com/Example/Proj", raw)
        self.assertEqual(normalize_origin(""), "")

    def test_id_from_root_and_origin(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_project(Path(tmp))
            (root / "src").mkdir()
            ref = detect(root / "src", home=Path(tmp) / "home")
            self.assertEqual(ref.root, root.resolve())
            self.assertEqual(ref.origin, "github.com/Example/Proj")
            self.assertEqual(ref.project_id, compute_id(root, "github.com/Example/Proj"))
            self.assertEqual(current_branch(root), "main")
            other = make_project(Path(tmp), "other", origin="git@github.com:Example/Other.git")
            self.assertNotEqual(detect(other).project_id, ref.project_id)
            self.assertIsInstance(ref, ProjectRef)
            self.assertEqual(ref.data_dir, Path(tmp) / "home" / "projects" / ref.project_id)


if __name__ == "__main__":
    unittest.main()
