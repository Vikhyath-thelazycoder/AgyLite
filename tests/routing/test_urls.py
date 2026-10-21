"""MP1 F1: URLs and bare domain names are masked before keyword rules, tags and BM25 see the request."""
import os
import sys
import unittest

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.insert(0, ROOT_DIR)

from agylite.routing import ProjectFacts, Router, capability_ids  # noqa: E402
from agylite.routing.classify import extract_urls  # noqa: E402


class TestExtractUrls(unittest.TestCase):
    def assert_masked(self, text, url):
        masked, urls = extract_urls(text)
        self.assertEqual(urls, [url])
        self.assertNotIn(url, masked)
        self.assertIn("urlref", masked)

    def assert_kept(self, text):
        self.assertEqual(extract_urls(text), (text, []))

    def test_masked(self):
        self.assert_masked("see stripe.com", "stripe.com")
        self.assert_masked("pricing at https://stripe.com/pricing?x=1.", "https://stripe.com/pricing?x=1")
        self.assert_masked("like linear.app", "linear.app")
        self.assert_masked("www.example.org/docs", "www.example.org/docs")
        self.assert_masked("docs.example.dev/api is stale", "docs.example.dev/api")

    def test_not_masked(self):
        for text in ("edit config.yaml", "release v1.2.3", "upgrade node.js", "fix next.config.ts",
                     "run deploy.sh", "update README.md"):
            with self.subTest(text):
                self.assert_kept(text)


class TestUrlRouting(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.router = Router()

    def ids(self, request, stage="unknown"):
        return capability_ids(self.router.route(request, project=ProjectFacts(stage=stage)))

    def test_brand_domain_is_not_a_payment_signal(self):
        ids = self.ids("Extract the design system from stripe.com and linear.app as inspiration")
        self.assertNotIn("engineering/security", ids)
        self.assertNotIn("engineering/backend", ids)

    def test_brand_word_outside_a_url_still_is(self):
        ids = self.ids("Add Stripe checkout to the pricing page", "existing")
        self.assertIn("engineering/security", ids)
        self.assertIn("engineering/backend", ids)

    def test_requires_urls_rule_needs_a_url(self):
        """MP4 §2.5: `requires_urls` rules (design-inspiration) fire only when the request carries a URL."""
        from agylite.routing.rules import match_rules
        cfg = {"rules": [{"id": "insp", "any": ["look like"], "select": ["design/inspiration-extract"],
                          "requires_urls": True}]}
        self.assertEqual(match_rules("make it look like urlref", cfg, "unknown"), [])
        self.assertEqual([h.rule for h in match_rules("make it look like urlref", cfg, "unknown", has_urls=True)], ["insp"])
        ids = [c["id"] for c in Router().route("Make the pricing page look like our old one")["capabilities"]]
        self.assertNotIn("design/inspiration-extract", ids)

    def test_route_lists_the_urls(self):
        r = self.router.route("Make our pricing page look like https://www.notion.so/pricing")
        self.assertEqual(r["urls"], ["https://www.notion.so/pricing"])
        self.assertEqual(self.router.route("Improve checkout security.")["urls"], [])


if __name__ == "__main__":
    unittest.main()
