"""MP4 §3.2: a DESIGN_CHANGE route with design/inspiration-extract gets an INSPIRATION step before PLAN, and the
BLOCKING question "DESIGN.md approved" (asked because of the route, not the words), so no task can start before the
owner approves the extracted DESIGN.md. Routes without it are unchanged."""
import os
import sys
import unittest

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.insert(0, ROOT_DIR)

from agylite.project import questions  # noqa: E402
from agylite.routing import ProjectFacts, Router  # noqa: E402

INSPIRED = "Extract the design system from stripe.com and linear.app as inspiration"


class TestInspirationFlow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.router = Router()

    def test_inspiration_step_comes_before_plan(self):
        steps = [s["step"] for s in self.router.route(INSPIRED, project=ProjectFacts(stage="existing"))["lifecycle"]]
        self.assertLess(steps.index("INSPIRATION"), steps.index("PLAN"))
        step = next(s for s in self.router.route(INSPIRED)["lifecycle"] if s["step"] == "INSPIRATION")
        self.assertIn("agylite design extract", " ".join(step["commands"]))
        self.assertIn("approved", step["exit"])
        plain = self.router.route("Make the landing page feel premium.")["lifecycle"] or []
        self.assertNotIn("INSPIRATION", [s["step"] for s in plain])

    def test_design_md_approval_is_a_blocking_question_for_the_route(self):
        bank = questions.load_bank()
        qs, _ = questions.next_questions(bank, INSPIRED, stage="existing",
                                         capabilities=["design/inspiration-extract", "design/design-system"])
        approval = next(q for q in qs if q["id"] == "design-md-approved")
        self.assertEqual(approval["priority"], "BLOCKING")
        qs, _ = questions.next_questions(bank, "Make it look like our old one", stage="existing",
                                         capabilities=["design/design-direction"])
        self.assertNotIn("design-md-approved", [q["id"] for q in qs])
        self.assertEqual(questions.validate_bank(bank), [])


if __name__ == "__main__":
    unittest.main()
