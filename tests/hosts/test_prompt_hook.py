"""MP1 F15 (D-048): the UserPromptSubmit hook routes every prompt, injects the route within budget, stays silent when
it should, never fails, and never records the prompt text."""
import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.insert(0, ROOT_DIR)

from tests.context.fixtures import make_project  # noqa: E402
from agylite.cli import main  # noqa: E402

PROMPT = "Add Stripe checkout to the pricing page"


class TestPromptHook(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        self.home = base / "home"
        self.root = make_project(base)
        self.env = mock.patch.dict(os.environ, {"AGYLITE_HOME": str(self.home)})
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.tmp.cleanup()

    def hook(self, stdin, session="s-hook"):
        if isinstance(stdin, dict):
            stdin = json.dumps({"session_id": session, "cwd": str(self.root), "hook_event_name": "UserPromptSubmit",
                                **stdin})
        out = io.StringIO()
        with contextlib.redirect_stdout(out), mock.patch("sys.stdin", io.StringIO(stdin)):
            code = main(["hook", "prompt", "--host", "claude-code"])
        return code, out.getvalue()

    def test_code_change_prompt_gets_route_load_line_and_cards_within_budget(self):
        code, out = self.hook({"prompt": PROMPT})
        self.assertEqual(code, 0)
        lines = out.splitlines()
        self.assertTrue(lines[0].startswith("Agylite route: "), out)
        self.assertIn("engineering/security", lines[0])
        # no bundle installed in this home: the load line falls back to the context command
        self.assertTrue(lines[1].startswith(f'Before the first edit, load the whole skill and follow it: '
                                            f'agylite context --request "{PROMPT}"'))
        self.assertIn("Done means: agylite verify passes", lines[2])
        self.assertIn("# engineering/", out)                     # at least one L1 card
        self.assertLessEqual(len(out.encode()) // 4, 800)

    def test_with_a_bundle_the_hook_names_the_whole_skill_to_load(self):
        """Plan B: the route arrives with `agylite skill load <upstream>/<name>` for the primary skill."""
        from tests.context.fixtures import make_bundle
        make_bundle(self.home)
        _, out = self.hook({"prompt": PROMPT})
        self.assertIn("Before the first edit, load the whole skill and follow it: agylite skill load alpha/", out)

    def test_compose_is_the_hook_text_without_side_effects(self):
        """The token report measures the hook with compose(): same text, no events, no fired marker."""
        from agylite.context import prompt_hook
        from agylite.context.budget import load_budgets
        from agylite.project.identity import detect
        out = prompt_hook.compose(PROMPT, detect(self.root), load_budgets())
        self.assertFalse((self.home / "hosts" / "prompt-hook.json").exists())
        self.assertEqual(list(self.home.glob("projects/*/events/*.jsonl")), [])
        _, printed = self.hook({"prompt": PROMPT}, session=None)
        self.assertEqual(out["text"], printed)
        self.assertIsNone(prompt_hook.compose("hello there", detect(self.root), load_budgets()))

    def test_silent_cases(self):
        for stdin in ({"prompt": "Translate my grandmother's recipe into Italian"},   # unmatched
                      {"prompt": "yes"}, {"prompt": "go on please"}, {"prompt": "/help me with the review"},
                      "not json", "", {"no_prompt": 1}):
            with self.subTest(stdin):
                self.assertEqual(self.hook(stdin), (0, ""))

    def test_off_switch(self):
        with mock.patch("agylite.context.prompt_hook.load_discipline", return_value={"prompt_hook": "off"}):
            self.assertEqual(self.hook({"prompt": PROMPT}), (0, ""))

    def test_internal_error_prints_nothing(self):
        with mock.patch("agylite.context.prompt_hook.build", side_effect=RuntimeError("boom")):
            self.assertEqual(self.hook({"prompt": PROMPT}), (0, ""))

    def test_second_call_in_the_same_session_marks_cards(self):
        _, first = self.hook({"prompt": PROMPT})
        _, second = self.hook({"prompt": PROMPT})
        self.assertIn("(card engineering/security already in context)", second)
        self.assertLess(len(second), len(first))
        _, other = self.hook({"prompt": PROMPT}, session="s-other")
        self.assertNotIn("already in context", other)

    def test_events_never_contain_the_prompt(self):
        self.hook({"prompt": PROMPT})
        self.hook({"prompt": "Translate my grandmother's recipe into Italian"})
        logs = list(self.home.rglob("events/*.jsonl"))
        self.assertTrue(logs)
        text = "".join(p.read_text(encoding="utf-8") for p in logs)
        self.assertIn("PROMPT_ROUTED", text)
        self.assertIn("ROUTE_UNMATCHED", text)
        self.assertNotIn("Stripe", text)
        self.assertNotIn("grandmother", text)
        self.assertTrue((self.home / "hosts" / "prompt-hook.json").is_file())


if __name__ == "__main__":
    unittest.main()
