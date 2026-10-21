"""Router behaviour (P8): config validation, change types, paths, stages, suppression, BM25 fallback, conflicts, CLI."""
import contextlib
import copy
import io
import json
import os
import sys
import unittest

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.insert(0, ROOT_DIR)

from agylite.cli import main  # noqa: E402
from agylite.routing import ProjectFacts, Router, RoutingError, capability_ids  # noqa: E402
from agylite.routing.classify import CHANGE_TYPES, classify_change, normalize  # noqa: E402
from agylite.routing.fallback_bm25 import BM25  # noqa: E402
from agylite.routing.rules import validate_routing  # noqa: E402


class TestRoutingConfig(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.router = Router()

    def test_config_valid(self):
        self.assertEqual(validate_routing(self.router.cfg, self.router.cards, self.router.hierarchy), [])

    def test_conflict_hierarchy_order(self):
        h = self.router.hierarchy
        self.assertEqual(sorted(h, key=h.get)[:4],
                         ["user-requirements", "project-security", "project-architecture", "engineering-methodology"])

    def test_validator_catches_planted_errors(self):
        cfg = copy.deepcopy(self.router.cfg)
        cfg["rules"][0]["select"].append("engineering/nonexistent")
        cfg["rules"].append({"id": "bad", "any": ["x"], "select": ["seo/evidence"]})
        cfg["rules"].append({"id": "bad2", "any": ["y"], "select": ["engineering/simplicity"]})
        cfg["change_types"]["order"].pop()
        cfg["change_type_adds"] = {"types": ["MIGRATION_CHANGE"], "add": ["engineering/nope"]}
        problems = " | ".join(validate_routing(cfg, self.router.cards, self.router.hierarchy))
        self.assertIn("change_type_adds: unknown change type MIGRATION_CHANGE", problems)
        self.assertIn("change_type_adds: unknown capability engineering/nope", problems)
        self.assertIn("unknown capability engineering/nonexistent", problems)
        self.assertIn("seo/evidence is internal", problems)
        self.assertIn("engineering/simplicity is explicit-only", problems)
        self.assertIn("spec §54", problems)


class TestClassify(unittest.TestCase):
    def setUp(self):
        self.cfg = Router().cfg["change_types"]

    def test_all_change_types_reachable(self):
        samples = {
            "SECURITY_CHANGE": "harden the auth middleware", "SEO_CHANGE": "improve our sitemap",
            "MEDIA_CHANGE": "record a demo", "OBSERVABILITY_CHANGE": "add structured logging",
            "PERFORMANCE_CHANGE": "the orders page is slow", "BUG_FIX": "the export crashes on empty rows",
            "TESTING_CHANGE": "raise coverage on the parser", "REFACTOR": "restructure the billing module",
            "DESIGN_CHANGE": "tighten the spacing on cards", "INFRA_CHANGE": "move hosting to docker",
            "DOCUMENTATION_CHANGE": "update the readme", "PLAN_CHANGE": "reprioritize the roadmap",
            "FEATURE_CHANGE": "tweak the booking confirmation", "NEW_FEATURE": "add CSV import",
        }
        self.assertEqual(set(samples), set(CHANGE_TYPES))
        for expected, text in samples.items():
            self.assertEqual(classify_change(normalize(text), self.cfg, None)[0], expected, text)

    def test_word_boundaries_and_plurals(self):
        self.assertEqual(classify_change(normalize("Ship the pre-fixed build"), self.cfg, None)[0], "NEW_FEATURE")
        self.assertEqual(classify_change(normalize("Two bugs in checkout"), self.cfg, None)[0], "BUG_FIX")


class TestRouter(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.router = Router()

    def ids(self, text, stage="unknown", **kw):
        return capability_ids(self.router.route(text, project=ProjectFacts(stage=stage), **kw))

    def test_new_project_never_routes_codebase(self):
        self.assertFalse([i for i in self.ids("Build a SaaS application and trace dependencies", "new")
                          if i.startswith("codebase/")])

    def test_existing_project_adds_impact_analysis(self):
        self.assertIn("codebase/impact-analysis", self.ids("Fix the crash in the export endpoint", "existing"))
        self.assertNotIn("codebase/impact-analysis", self.ids("Fix the crash in the export endpoint", "new"))

    def test_multi_step_changes_add_completion(self):
        """MP3 §3.1 (owner decision 2026-10-21): Unlazy's completion gate joins every code-changing task as a
        dependency (not counted in max_capabilities); quick questions and design/SEO/media/plan/docs/testing do not."""
        cfg = self.router.cfg["change_type_adds"]
        self.assertEqual(cfg["add"], ["engineering/completion"])
        self.assertEqual(set(cfg["types"]), {"NEW_FEATURE", "FEATURE_CHANGE", "BUG_FIX", "REFACTOR",
                                             "SECURITY_CHANGE", "PERFORMANCE_CHANGE"})
        r = self.router.route("Fix the off-by-one bug in pagination", project=ProjectFacts(stage="existing"))
        self.assertEqual(r["change_type"], "BUG_FIX")
        dep = next(d for d in r["dependencies"] if d["id"] == "engineering/completion")
        self.assertIn("BUG_FIX", dep["required_by"])
        self.assertNotIn("engineering/completion", [c["id"] for c in r["capabilities"]])
        for request in ("What does this function do?", "Make the landing page feel premium."):
            with self.subTest(request):
                self.assertNotIn("engineering/completion", capability_ids(self.router.route(request)))
        self.assertNotIn("engineering/completion",
                         capability_ids(self.router.route("Translate my grandmother's recipe into Italian")))

    def test_internal_capabilities_only_via_dependencies(self):
        result = self.router.route("Audit my website.")
        self.assertNotIn("seo/runtime", [c["id"] for c in result["capabilities"]])
        self.assertIn({"id": "seo/runtime", "required_by": "seo/auditing"}, result["dependencies"])

    def test_paths_select_capabilities(self):
        result = self.router.route("update this", paths=["src/auth/session.ts", "app/styles/main.css"])
        ids = capability_ids(result)
        self.assertIn("engineering/security", ids)
        self.assertIn("design/frontend", ids)
        self.assertTrue(any(r.startswith("path:") for r in result["rules"]))

    def test_requested_capability_and_unknown(self):
        self.assertIn("engineering/documentation", self.ids("hello", requested=["engineering/documentation"]))
        with self.assertRaises(RoutingError):
            self.router.route("hello", requested=["nope/nothing"])

    def test_stack_selects_stack_packs(self):
        result = self.router.route("add CSV import", project=ProjectFacts(stage="existing", stack=("python", "django")))
        self.assertIn("engineering/stack-packs", [d["id"] for d in result["dependencies"]])

    def test_nothing_routable(self):
        result = self.router.route("hello there")
        self.assertEqual((result["capabilities"], result["confidence"], result["method"]), ([], "none", "none"))

    def test_bm25_fallback_when_not_confident(self):
        self.assertIn("media/presentation", self.ids("prepare a slide deck about q3"))
        result = self.router.route("keep the documentation living alongside the code")
        self.assertEqual((result["method"], result["confidence"]), ("bm25", "low"))
        self.assertEqual(self.ids("keep the documentation living alongside the code"), ["engineering/documentation"])

    def test_bm25_needs_domain_signal(self):
        """MP1 F3: one shared word or generic verbs are no domain signal; BM25 stays inside the agreed domain."""
        self.assertEqual(self.router.route("translate the app into french")["method"], "none")
        self.assertEqual([i for i in self.ids("Summarise this YouTube video for me") if i.startswith("media/")], [])
        self.assertEqual([i for i in self.ids("Grill me on this plan before I build it")
                          if i.startswith("media/") or i == "testing/local-verification"], [])

    def test_bm25_not_used_when_rules_confident(self):
        self.assertEqual(self.router.route("Fix the payment webhook security.")["method"], "rules")

    def test_bm25_ranking(self):
        index = BM25({"a": "payment webhook signature", "b": "landing page typography", "c": "webhook retries"})
        self.assertEqual(index.top("webhook signature", 3, 0.1)[0][0], "a")
        self.assertEqual(index.top("unrelated words", 3, 0.1), [])

    def test_declared_conflict_drops_lower_ranked(self):
        cards = copy.deepcopy(self.router.cards)
        cards["engineering/security"]["conflicts"] = ["design/frontend"]
        cards["design/frontend"]["conflicts"] = ["engineering/security"]
        result = Router(cards=cards).route("harden the login page css", paths=["src/auth/x.ts", "a.css"])
        ids = capability_ids(result)
        self.assertIn("engineering/security", ids)
        self.assertNotIn("design/frontend", ids)
        self.assertTrue(any("conflicts with engineering/security" in s["reason"] for s in result["suppressed"]))

    def test_guidance_order_follows_hierarchy(self):
        caps = self.router.route("Fix the payment webhook security.", project=ProjectFacts(stage="existing"))["capabilities"]
        levels = [c["level"] for c in caps]
        self.assertEqual(levels, sorted(levels))
        self.assertEqual(caps[0]["id"], "engineering/security")

    def test_disabled_capability_never_selected(self):
        cards = copy.deepcopy(self.router.cards)
        cards["design/typography"]["enabled"] = False
        self.assertNotIn("design/typography", capability_ids(Router(cards=cards).route("Make the landing page feel premium.")))


class TestRouteCli(unittest.TestCase):
    def setUp(self):   # `route` emits events: keep them out of the real $AGYLITE_HOME
        import tempfile
        from unittest import mock
        self.tmp = tempfile.TemporaryDirectory()
        self.env = mock.patch.dict(os.environ, {"AGYLITE_HOME": self.tmp.name})
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.tmp.cleanup()

    def run_cli(self, *argv):
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            code = main(list(argv))
        return code, out.getvalue()

    def test_json_output(self):
        code, out = self.run_cli("route", "Fix", "the", "payment", "webhook", "security.", "--existing")
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertEqual((data["change_type"], data["project"]["stage"]), ("SECURITY_CHANGE", "existing"))

    def test_brief_and_errors(self):
        code, out = self.run_cli("route", "Audit my website.", "--brief")
        self.assertEqual(code, 0)
        self.assertTrue(out.startswith("SEO_CHANGE · high (rules) · "), out)
        self.assertEqual(self.run_cli("route", "x", "--capability", "nope/x")[0], 2)


if __name__ == "__main__":
    unittest.main()
