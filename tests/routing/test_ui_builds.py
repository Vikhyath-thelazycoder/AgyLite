"""MP4 Tier 1 finding (2026-10-22): building a page, site or app screen routes to design/design-direction first, so
Taste is the skill that loads whole. Before the fix, "Make a one-page website…" offered Addy's security skill and
Pocock's tdd, and "Build the main screen of … app" offered Addy's incremental-implementation; "spending plan" made it a
PLAN_CHANGE and "no screenshots" a TESTING_CHANGE."""
import json
import os
import sys
import unittest
from pathlib import Path

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.insert(0, ROOT_DIR)

from agylite.routing import ProjectFacts, Router  # noqa: E402

EVALS = Path(os.environ.get("AGYLITE_UPSTREAMS_DIR") or Path.home() / "Developer" / "os") / \
    "taste-skill" / "skills" / "taste-skill" / "evals" / "evals.json"

# The opening of each Taste v2.1 eval prompt (evals/evals.json), with the words that misrouted them.
PROMPTS = {
    1: "Build a landing page for Ledgerly, an invoicing tool for freelance designers. There is no existing brand and no "
       "screenshots; the product name is all we have. Plain static HTML, CSS and JS in one folder.",
    2: "Make a one-page website for Osteria Nove, a 38-seat Italian restaurant in Alfama, Lisbon. Reservations by phone "
       "or email. We have no photographs yet. Static HTML/CSS/JS.",
    3: "I'm Mara Lindqvist, a product designer in Stockholm. I need a portfolio homepage: six selected projects, a short "
       "about paragraph, and a way to contact me.",
    4: "Launch page for Kiln, a ceramic pour-over coffee set. One page, with a way to buy (a button is enough). "
       "Static HTML/CSS/JS.",
    5: "Website for Casa Mirante, a six-room guesthouse. One page: the rooms and how to book. Static HTML/CSS/JS.",
    6: "Landing page for Format, a two-day design conference in Rotterdam. Tickets at 390 euros. Static HTML/CSS/JS.",
    7: "Build the main screen of Ledgerly, a budgeting app for couples who share money: the October overview, the "
       "spending plan (planned against spent by category) and recent transactions. Static HTML/CSS/JS.",
    8: "Dashboard for Relay, an edge deployment platform for web teams: recent deployments, p95 latency, and usage "
       "against the plan's limits. Dark theme. Static HTML/CSS/JS.",
    9: "Workspace settings for Proofline, a design-review tool: members and roles, billing (current plan, seats, "
       "invoices) and notifications. Static HTML/CSS/JS, desktop and phone.",
    10: "The queue screen of Hearth, a support inbox for a six-person SaaS team, plus filters and saved views. "
        "Static HTML/CSS/JS.",
}


class TestUiBuildRouting(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.router = Router()

    def check(self, prompt):
        r = self.router.route(prompt, project=ProjectFacts(stage="new"))
        ids = [c["id"] for c in r["capabilities"]]
        self.assertEqual(r["whole_skills"][0], "design/design-direction", (r["whole_skills"], ids))
        self.assertNotIn(r["change_type"], ("TESTING_CHANGE", "PLAN_CHANGE"))
        if "static" in prompt.lower():   # a static page has no users, accounts or network exposure
            self.assertNotIn("engineering/security", ids)

    def test_taste_eval_openings(self):
        for i, prompt in PROMPTS.items():
            with self.subTest(eval=i):
                self.check(prompt)

    @unittest.skipUnless(EVALS.is_file(), "taste-skill clone not present")
    def test_full_taste_eval_prompts(self):
        for e in json.loads(EVALS.read_text(encoding="utf-8"))["evals"]:
            with self.subTest(eval=e["id"]):
                self.check(e["prompt"])

    def test_product_plans_and_missing_assets_do_not_set_the_change_type(self):
        cases = {"Plan the next milestone": "PLAN_CHANGE", "Add tests for the parser": "TESTING_CHANGE",
                 "Show the pricing plan on the page": None, "Build the page; we have no screenshots yet": None}
        for prompt, want in cases.items():
            with self.subTest(prompt):
                got = self.router.route(prompt)["change_type"]
                if want:
                    self.assertEqual(got, want)
                else:
                    self.assertNotIn(got, ("PLAN_CHANGE", "TESTING_CHANGE"))

    def test_a_product_with_accounts_keeps_security(self):
        r = self.router.route("Build a SaaS web app with user accounts and payments", project=ProjectFacts(stage="new"))
        self.assertIn("engineering/security", [c["id"] for c in r["capabilities"]])


if __name__ == "__main__":
    unittest.main()
