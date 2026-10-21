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


if __name__ == "__main__":
    unittest.main()
