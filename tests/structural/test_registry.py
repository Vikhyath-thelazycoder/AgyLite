import contextlib
import copy
import io
import os
import re
import subprocess
import sys
import unittest

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.insert(0, ROOT_DIR)

from agylite.cli import main  # noqa: E402
from agylite.registry import generate, loader, schema  # noqa: E402

EXPECTED_CAPABILITIES = 76  # D-035: + testing/evidence; MP4 §2.5: + design/inspiration-extract; MP5: + 5 research, 6 youtube, engineering/diagrams
def _expected_bundled_files():
    """Bundled files per the generated extraction summary (COPY + ADAPT + PRESERVE + GENERATED, MP3 §2.1). Upstream updates (P28) change the
    number; these tests check that provenance, registry and licenses all agree with the audited extraction matrix."""
    import json as _json
    with open(os.path.join(ROOT_DIR, "docs", "audit", "evidence", "extraction-summary.json"), encoding="utf-8") as f:
        repos = _json.load(f)["repos"]
    return sum(d.get(k, {}).get("files", 0) for d in repos.values() for k in ("COPY", "ADAPT", "PRESERVE", "GENERATED"))


EXPECTED_BUNDLED_FILES = _expected_bundled_files()
# Files P7 retired in favour of capabilities/**/card.yaml (C-1); only history documents may still name them.
RETIRED = re.compile(r"config/capabilities\.yaml|domain-model\.yaml|(?<![\w./-])integrations/(?:\*\.yaml|<name>|ecc|`| +#)|├── capabilities\.yaml")
HISTORY = ("CHANGELOG.md", "docs/audit/", "docs/plan/", "docs/evidence/")


class TestRegistrySource(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cards = loader.load_cards()

    def test_exactly_one_registry_source(self):
        for retired in ("config/capabilities.yaml", "integrations", "tools/audit/domain-model.yaml"):
            self.assertFalse(os.path.exists(os.path.join(ROOT_DIR, retired)), f"{retired} must be removed (P7)")
        self.assertEqual(len(self.cards), EXPECTED_CAPABILITIES)

    def test_no_references_to_retired_registries(self):
        files = subprocess.run(["git", "ls-files"], cwd=ROOT_DIR, capture_output=True, text=True).stdout.split()
        offenders = []
        for rel in files:
            if rel.startswith(HISTORY) or rel == "tests/structural/test_registry.py" or not os.path.isfile(
                    os.path.join(ROOT_DIR, rel)):
                continue
            with open(os.path.join(ROOT_DIR, rel), encoding="utf-8", errors="ignore") as f:
                for n, line in enumerate(f, 1):
                    if RETIRED.search(line):
                        offenders.append(f"{rel}:{n}")
        self.assertEqual(offenders, [])

    def test_registry_check_is_clean(self):
        self.assertEqual(generate.check(), [])

    def test_ids_are_domain_first(self):
        upstream = {n.split("/")[-1].lower() for n in generate.upstream_names()}
        for cid in self.cards:
            self.assertTrue(schema.ID.match(cid), cid)
            self.assertFalse(upstream & set(cid.split("/")), f"{cid} uses an upstream repository name")

    def test_web_qa_classes_recorded(self):
        testing = {cid: c for cid, c in self.cards.items() if cid.startswith("testing/")}
        self.assertEqual(len(testing), 9)
        self.assertTrue(all(c["web_qa_class"] in schema.WEB_QA_CLASSES for c in testing.values()))
        self.assertEqual(testing["testing/local-verification"]["web_qa_class"], "CORE")

    def test_browser_verification_disabled_by_policy(self):
        # D-035: the only browser card is disabled, has no sources, and every mode is DISABLED_BY_POLICY.
        exc = self.cards["testing/browser-exception"]
        self.assertFalse(exc["enabled"])
        self.assertEqual(exc["runtime_status"], "DISABLED_BY_POLICY")
        self.assertEqual(set(exc["web_qa_modes"].values()), {"DISABLED_BY_POLICY"})
        self.assertNotIn("FALLBACK", schema.WEB_QA_CLASSES)
        outside = [cid for cid, c in self.cards.items()
                   if c["requires_browser"] != "none" and cid.split("/")[0] not in schema.BROWSER_SCOPED_DOMAINS
                   and cid not in schema.BROWSER_SCOPED_CAPABILITIES]
        self.assertEqual(outside, [])

    def test_browser_need_outside_scoped_domains_rejected(self):
        cards = loader.load_cards()
        cards["testing/regression"]["requires_browser"] = "fallback"
        cards["testing/browser-exception"]["enabled"] = True
        p = schema.validate_cards(cards)
        self.assertTrue(any("testing/regression: requires_browser must be none" in x for x in p), p)
        self.assertTrue(any("DISABLED_BY_POLICY requires enabled: false" in x for x in p), p)

    def test_card_docs_within_l1_budget(self):
        for cid in self.cards:
            size = (loader.capabilities_dir() / cid / "CARD.md").stat().st_size
            self.assertLessEqual(size, generate.CARD_MAX_BYTES, cid)

    def test_defaults_are_merged(self):
        events, security = self.cards["observability/events"], self.cards["engineering/security"]
        self.assertEqual(events["activation_conditions"]["mode"], "internal")
        self.assertEqual(events["priority"], 50)
        self.assertEqual(security["priority"], 90)
        self.assertEqual(set(security["host_compatibility"]), {"claude-code", "codex", "cursor", "antigravity"})
        self.assertTrue(all(h["status"] == "NOT_VERIFIED" for h in security["host_compatibility"].values()))  # D-024

    def test_spec_routing_example_capabilities_exist_and_relate(self):
        # spec §14: "Improve checkout security" -> engineering/security, codebase/impact-analysis, testing/security
        related = self.cards["engineering/security"]["related_capabilities"]
        self.assertIn("testing/security", related)
        self.assertIn("codebase/impact-analysis", related)
        self.assertEqual(self.cards["engineering/simplicity"]["activation_conditions"]["mode"], "explicit")


class TestGeneratedRegistry(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reg = generate.plan_registry()

    def test_every_spec_field_for_every_capability(self):
        caps = self.reg["capabilities"]
        self.assertEqual(len(caps), EXPECTED_CAPABILITIES)
        for cid, entry in caps.items():
            self.assertEqual(list(entry)[:len(schema.SPEC_FIELDS)], list(schema.SPEC_FIELDS), cid)

    def test_provenance_fields_are_derived(self):
        caps = self.reg["capabilities"]
        self.assertEqual(sum(e["token_cost_estimate"]["bundled_files"] for e in caps.values()), EXPECTED_BUNDLED_FILES)
        self.assertEqual(caps["testing/browser-exception"]["token_cost_estimate"]["bundled_files"], 0)
        self.assertEqual(caps["testing/browser-exception"]["runtime_status"], "DISABLED_BY_POLICY")
        self.assertEqual(caps["design/frontend"]["runtime_status"], "ACTIVE")
        self.assertIn("Appllama/appllama-skills", caps["design/frontend"]["source_repositories"])
        self.assertIn("Appllama/appllama-skills", caps["design/motion"]["source_repositories"])
        sec = caps["engineering/security"]
        self.assertEqual(sorted(sec["source_paths"]), sec["source_repositories"])
        self.assertEqual(set(sec["commit_sha"]), set(sec["source_repositories"]))
        self.assertTrue(all(re.match(r"^[0-9a-f]{40}$", s) for s in sec["commit_sha"].values()))
        self.assertEqual(caps["observability/events"]["integration_type"], ["OS_NATIVE"])
        self.assertEqual(caps["observability/events"]["source_repositories"], [])

    def test_generation_is_deterministic(self):
        self.assertEqual(generate.plan_registry(), self.reg)


class TestValidators(unittest.TestCase):
    def setUp(self):
        self.cards = copy.deepcopy(loader.load_cards())

    def problems(self):
        return " | ".join(schema.validate_cards(self.cards))

    def test_valid_cards_have_no_problems(self):
        self.assertEqual(self.problems(), "")

    def test_generated_field_in_card_rejected(self):
        self.cards["engineering/review"]["license"] = "MIT"
        self.assertIn("generated and must not be authored", self.problems())

    def test_unknown_reference_and_fallback_rejected(self):
        self.cards["engineering/review"]["related_capabilities"] = ["engineering/nope"]
        self.cards["engineering/review"]["fallback_capability"] = "engineering/review"
        p = self.problems()
        self.assertIn("unknown capability engineering/nope", p)
        self.assertIn("fallback_capability must be another known capability", p)

    def test_security_class_must_match_needs(self):
        self.cards["seo/auditing"]["security_class"] = "read-only"
        self.assertIn("security_class network or privileged", self.problems())

    def test_conflicts_must_be_symmetric(self):
        self.cards["media/demo"]["conflicts"] = ["engineering/backend"]
        self.assertIn("not declared on both cards", self.problems())
        self.cards["engineering/backend"]["conflicts"] = ["media/demo"]
        self.assertEqual(self.problems(), "")

    def test_testing_needs_web_qa_class(self):
        del self.cards["testing/regression"]["web_qa_class"]
        self.cards["design/ux"]["web_qa_class"] = "CORE"
        p = self.problems()
        self.assertIn("testing/regression: testing capability needs web_qa_class", p)
        self.assertIn("design/ux: web QA classes are only recorded for testing", p)

    def test_registry_origin_and_id_rules(self):
        reg = copy.deepcopy(generate.plan_registry())
        caps = reg["capabilities"]
        caps["observability/events"]["token_cost_estimate"]["bundled_files"] = 3
        caps["design/ux"]["token_cost_estimate"]["bundled_files"] = 0
        caps["ecc/thing"] = dict(caps["design/ux"], capability_id="ecc/thing", domain="ecc", subdomain="thing")
        p = " | ".join(schema.validate_registry(reg, generate.upstream_names()))
        self.assertIn("os-native capability must not own bundled files", p)
        self.assertIn("design/ux: bundled capability has no bundled source", p)
        self.assertIn("ecc/thing: capability ids are domain-first", p)


class TestCli(unittest.TestCase):
    def run_cli(self, *argv):
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            code = main(list(argv))
        return code, out.getvalue()

    def test_check_show_list(self):
        code, out = self.run_cli("registry", "check", "--no-bundle")
        self.assertEqual(code, 0, out)
        self.assertIn(f"{EXPECTED_CAPABILITIES} capabilities", out)
        code, out = self.run_cli("registry", "show", "engineering/security")
        self.assertEqual(code, 0)
        self.assertIn("priority: 90", out)
        self.assertEqual(self.run_cli("registry", "show", "nope/nope")[0], 1)


if __name__ == "__main__":
    unittest.main()
