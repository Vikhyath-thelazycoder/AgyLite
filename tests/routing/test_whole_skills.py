"""Plan B: the route names which capabilities' primary skills load whole — one, or two when strong rule signals span
two domains (IMPLEMENTATION_PLAN §2.1 rule 3)."""
import os
import sys
import unittest

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.insert(0, ROOT_DIR)

from agylite.routing import ProjectFacts, Router, context_order  # noqa: E402


class TestWholeSkills(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.router = Router()

    def test_one_job_one_whole_skill(self):
        r = self.router.route("Make the landing page feel premium.")
        self.assertEqual(len(r["whole_skills"]), 1)
        self.assertEqual(r["whole_skills"][0], r["capabilities"][0]["id"])

    def test_two_domains_two_whole_skills(self):
        r = self.router.route("Fix the SEO issues and add tests", project=ProjectFacts(stage="existing"))
        doms = {c.split("/")[0] for c in r["whole_skills"]}
        self.assertEqual(len(r["whole_skills"]), 2, r["whole_skills"])
        self.assertEqual(len(doms), 2)

    def test_highest_ranked_not_first_listed(self):
        """§2.1 rule 3: the highest-ranked capability loads whole. "checkout" adds security (score 2, listed first by
        the lifecycle) but the request is a diagnosis (score 3)."""
        r = self.router.route("Diagnose why the checkout test is flaky", project=ProjectFacts(stage="existing"))
        self.assertEqual(r["capabilities"][0]["id"], "engineering/security")
        self.assertEqual(r["whole_skills"][0], "engineering/debugging")
        self.assertEqual(context_order(r)[0], "engineering/debugging")
        self.assertEqual(sorted(context_order(r)), sorted(c["id"] for c in r["capabilities"]))
        self.assertEqual(self.router.route("Improve checkout security.")["whole_skills"][0], "engineering/security")

    def test_unmatched_loads_nothing(self):
        self.assertEqual(self.router.route("Translate my grandmother's recipe into Italian")["whole_skills"], [])



class TestSkillHints(unittest.TestCase):
    """D-050 / Phase 9 diagnosis item 3: the eng-pocock and eng-addy traces loaded the wrong original skill."""
    POCOCK = "files/pocock/skills/engineering/"

    @classmethod
    def setUpClass(cls):
        cls.router = Router()

    def route(self, text):
        return self.router.route(text, project=ProjectFacts(stage="existing"))

    def test_spec_and_tickets_name_their_pocock_skill(self):
        r = self.route("We've already discussed tagging in NOTES-DISCUSSION.md. Turn it into a spec and save it.")
        self.assertEqual(r["skill_hints"], {"engineering/planning": self.POCOCK + "to-spec/SKILL.md"})
        r = self.route("Break docs/specs/export.md into tickets.")
        self.assertEqual(r["whole_skills"][0], "engineering/planning")
        self.assertEqual(r["skill_hints"], {"engineering/planning": self.POCOCK + "to-tickets/SKILL.md"})
        self.assertEqual(self.route("Grill me on my plan to move note storage to a server.")["skill_hints"], {})

    def test_reviewing_a_diff_that_adds_code_is_a_review(self):
        r = self.route("Review the provided diff that adds a user-search endpoint. Deliver a structured review.")
        self.assertEqual(r["whole_skills"][0], "engineering/review")

    def test_test_first_fix_routes_to_testing_strategy(self):
        r = self.route("Discount codes over 100% make cart totals negative. Fix it test-first.")
        self.assertFalse(r["unmatched"])
        self.assertEqual(r["whole_skills"][0], "testing/strategy")

    def test_a_version_named_in_a_regression_is_not_release_work(self):
        r = self.route("parseLog got about 10x slower in release 2.3.0. Diagnose it.")
        self.assertEqual(r["whole_skills"][0], "engineering/debugging")
        self.assertNotIn("testing/release-verification", [c["id"] for c in r["capabilities"]])
        self.assertIn("engineering/release", [c["id"] for c in self.route("Cut a release for 2.4")["capabilities"]])


if __name__ == "__main__":
    unittest.main()
