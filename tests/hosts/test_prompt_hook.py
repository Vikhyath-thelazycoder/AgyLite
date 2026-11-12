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

    def test_with_a_bundle_the_hook_carries_the_whole_primary_skill(self):
        """MP3/MP4 Tier 1: agents rarely ran `agylite skill load` (0 of 37, then 2 of 3), so the primary skill's text
        arrives with the prompt, whole; a second prompt in the session gets a marker instead of the text again."""
        from tests.context.fixtures import make_bundle
        make_bundle(self.home)
        _, out = self.hook({"prompt": PROMPT})
        self.assertIn("The whole skill alpha/hardening follows; follow it before the first edit.", out)
        self.assertIn("### files/alpha/skills/hardening/SKILL.md — hardening (skill alpha/hardening, whole)", out)
        self.assertIn("## Headers", out)
        self.assertIn("## Cookies", out)                         # never truncated
        self.assertNotIn("agylite skill load alpha/hardening", out)
        _, again = self.hook({"prompt": PROMPT})
        self.assertIn("[cached] files/alpha/skills/hardening/SKILL.md", again)
        self.assertNotIn("## Cookies", again)

    def with_cap(self, max_chars, pairs=None, prompt=PROMPT):
        """The hook output under `prompt_hook.max_chars` (and `skill_overlaps` replaced by `pairs` when given)."""
        from agylite.context.budget import load_budgets
        from tests.context.fixtures import make_bundle
        make_bundle(self.home)
        budgets = load_budgets()
        if max_chars is not None:
            budgets["prompt_hook"]["max_chars"] = max_chars
        with contextlib.ExitStack() as stack:
            if pairs is not None:
                stack.enter_context(mock.patch("agylite.context.levels.skill_overlaps", return_value=pairs))
            stack.enter_context(mock.patch("agylite.context.budget.load_budgets", return_value=budgets))
            return self.hook({"prompt": prompt})[1]

    def test_the_whole_hook_stays_under_the_char_cap(self):
        """C1-2 (Step 3 part 2): Claude Code saves hook output over ~10k chars to a file the agent may never open."""
        from agylite.context.budget import load_budgets
        cap = load_budgets()["prompt_hook"]["max_chars"]
        self.assertTrue(9000 <= cap <= 10000, cap)
        out = self.with_cap(None)
        self.assertIn("## Cookies", out)
        self.assertLessEqual(len(out), cap)

    def test_a_lead_skill_over_the_cap_becomes_one_read_of_its_file(self):
        out = self.with_cap(600)
        self.assertLessEqual(len(out), 600)
        self.assertRegex(out, r"Before the first edit, read the whole skill alpha/hardening and follow it: \S*"
                              r"files/alpha/skills/hardening/SKILL\.md")
        self.assertNotIn("## Cookies", out)
        again = self.with_cap(600)   # not sent, so not marked as already in context
        self.assertNotIn("[cached]", again)
        self.assertIn("read the whole skill alpha/hardening", again)

    def overlap(self, pairs, max_chars=20000):
        """The hook output with `skill_overlaps` replaced by `pairs`; fixture skills are ~6k chars each, so the pairing
        tests lift the cap."""
        return self.with_cap(max_chars, pairs)

    def test_overlapping_skill_of_another_upstream_loads_whole_with_a_lead(self):
        """Option 2 (owner 2026-10-22, D-050): one job, two upstreams → both skills whole, the lead named and first."""
        hard, other = "files/alpha/skills/hardening/SKILL.md", "files/beta/skills/test-security/SKILL.md"
        out = self.overlap([(hard, other)])
        self.assertIn("The whole skills alpha/hardening and beta/test-security follow (one job, two upstreams); "
                      "follow both before the first edit, and where they disagree follow alpha/hardening.", out)
        self.assertIn("## Cookies", out)
        self.assertIn("## Authz tests", out)                     # the partner, whole
        self.assertLess(out.index("(skill alpha/hardening, whole)"), out.index("(skill beta/test-security, whole)"))

    def test_routed_skill_on_the_also_side_still_puts_the_lead_first(self):
        hard, other = "files/alpha/skills/hardening/SKILL.md", "files/beta/skills/test-security/SKILL.md"
        out = self.overlap([(other, hard)])
        self.assertIn("where they disagree follow beta/test-security.", out)
        self.assertLess(out.index("(skill beta/test-security, whole)"), out.index("(skill alpha/hardening, whole)"))

    def test_a_partner_that_would_break_the_cap_is_left_out(self):
        pairs = [("files/alpha/skills/hardening/SKILL.md", "files/beta/skills/test-security/SKILL.md")]
        full = self.overlap(pairs)
        cards = full.index("### files/") - full.index("# engineering/")
        cap = len(full) - cards - 1   # the pair alone is one char over: cards go first, then the partner
        self.tmp.cleanup(); self.setUp()   # a fresh home: nothing cached yet
        out = self.overlap(pairs, max_chars=cap)
        self.assertLessEqual(len(out), cap)
        self.assertIn("The whole skill alpha/hardening follows;", out)
        self.assertIn("## Cookies", out)
        self.assertNotIn("## Authz tests", out)

    def test_a_second_whole_skill_never_joins_the_hook(self):
        """C1-5 / C1-11: at most the lead and its overlap partner; a route's second whole skill (another domain) made
        the largest payloads as a 3rd skill."""
        from agylite.context import prompt_hook
        from agylite.routing import Router
        route = Router.route

        def two(self, *a, **k):
            r = route(self, *a, **k)
            r["whole_skills"] = [c["id"] for c in r["capabilities"]][:2]
            return r
        with mock.patch.object(Router, "route", two), \
                mock.patch.object(prompt_hook, "primary_skill_ids", wraps=prompt_hook.primary_skill_ids) as ids:
            out = self.with_cap(None)
        self.assertEqual(len(ids.call_args.args[1]), 1, ids.call_args)
        self.assertNotIn("Also load", out)
        self.assertNotIn("agylite skill load", out)

    def test_creative_routes_lift_ponytail_for_the_task(self):
        """C2-1 / C3-3 (Step 3 part 4, option A): youtube, media and diagram leads iterate; code work keeps Ponytail."""
        from agylite.context.prompt_hook import PONYTAIL_OFF
        for prompt in ("Write a YouTube script for my video about desk lamps", "Sequence diagram of the login flow",
                       "Make a 60 second launch video for our app"):
            _, out = self.hook({"prompt": prompt})
            self.assertEqual(out.splitlines()[1], PONYTAIL_OFF, (prompt, out[:300]))
        _, out = self.hook({"prompt": PROMPT})
        self.assertNotIn(PONYTAIL_OFF, out)

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
