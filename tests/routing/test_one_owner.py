"""Step 4 (doc 23 §3 guarantees 1–3): one owner per job. A route leads with one whole skill (plus its overlap partner);
two skills that do the same job never load together, and a demoted (route_excluded) skill never leads."""
import os
import sys
import unittest
from pathlib import Path

import yaml

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.insert(0, ROOT_DIR)

from agylite.bundle import rules  # noqa: E402
from agylite.context import levels  # noqa: E402
from agylite.registry import generate, loader  # noqa: E402
from agylite.routing import ProjectFacts, Router  # noqa: E402

# Each job's candidate skills; the first is the owner. At most one per job may load, and only the owner.
JOBS = {
    "security audit": ["files/cfsecurity/skills/security-audit/SKILL.md", "files/gstack/cso/SKILL.md",
                       "files/ecc/skills/security-review/SKILL.md", "files/ecc/agents/security-reviewer.md",
                       "files/addy/agents/security-auditor.md",
                       "files/agency/security/security-appsec-engineer.md",
                       "files/agency/security/security-penetration-tester.md",
                       "files/agency/security/security-ai-generated-code-auditor.md"],
    "secure coding": ["files/addy/skills/security-and-hardening/SKILL.md"],
    "variants": ["files/tob/plugins/variant-analysis/skills/variant-analysis/SKILL.md"],
    "footguns": ["files/tob/plugins/sharp-edges/skills/sharp-edges/SKILL.md"],
    "guardrails": ["files/gstack/careful/SKILL.md", "files/ecc/skills/safety-guard/SKILL.md"],
    "landing look": ["files/taste/skills/taste-skill/SKILL.md"],
    "landing content": ["files/elaya/skills/landing-page-design/SKILL.md"],
}


def loaded_skills(route, prios):
    """What the prompt hook loads, from config alone: the lead capability's hinted or first-priority skill and the
    overlap partner the route's rules allow."""
    cid = (route["whole_skills"] or [c["id"] for c in route["capabilities"]])[:1]
    if not cid:
        return []
    lead = route["skill_hints"].get(cid[0]) or (prios.get(cid[0]) or [None])[0]
    out = [lead] if lead else []
    for a, b in levels.skill_overlaps(rules=route["rules"]):
        if lead in (a, b):
            out.append(b if lead == a else a)
    return out


class TestOneOwnerPerJob(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.router = Router()
        cls.prios = levels.source_priorities()
        doc = yaml.safe_load((Path(ROOT_DIR) / "tests" / "routing" / "scenarios.yaml").read_text(encoding="utf-8"))
        cls.scenarios = [s for s in doc["scenarios"]
                         if any(w in (s["request"] + s["id"]).lower() for w in ("secur", "harden", "variant", "footgun",
                                                                                 "semgrep", "landing", "pricing page"))]

    def route(self, s):
        return self.router.route(s["request"], project=ProjectFacts(stage=s.get("stage", "unknown")))

    def test_security_and_landing_scenarios_load_one_owner_per_job(self):
        self.assertGreaterEqual(len(self.scenarios), 12)
        excluded = set(levels.route_excluded())
        for s in self.scenarios:
            with self.subTest(s["id"]):
                skills = loaded_skills(self.route(s), self.prios)
                self.assertFalse(set(skills) & excluded, skills)
                for job, cands in JOBS.items():
                    hit = [p for p in skills if p in cands]
                    self.assertLessEqual(len(hit), 1, (job, hit))
                    if hit:
                        self.assertEqual(hit[0], cands[0], job)

    def test_each_job_reaches_its_owner(self):
        want = {"s4-security-review": "security audit", "s14-checkout-security": "security audit",
                "s4-secure-coding": "secure coding", "s4-harden": "secure coding", "s4-variant-analysis": "variants",
                "s4-sharp-edges": "footguns"}
        by_id = {s["id"]: s for s in self.scenarios}
        for sid, job in want.items():
            with self.subTest(sid):
                self.assertEqual(loaded_skills(self.route(by_id[sid]), self.prios)[0], JOBS[job][0])

    def test_landing_build_pairs_taste_with_elaya_and_a_dashboard_does_not(self):
        build = self.router.route("Build a landing page for our AI note-taking app with a waitlist",
                                  project=ProjectFacts(stage="new"))
        self.assertEqual(loaded_skills(build, self.prios), [JOBS["landing look"][0], JOBS["landing content"][0]])
        dash = self.router.route("Build a settings page for workspace admins", project=ProjectFacts(stage="existing"))
        self.assertNotIn(JOBS["landing content"][0], loaded_skills(dash, self.prios))


class TestRouteExcludedCheck(unittest.TestCase):
    def test_no_route_excluded_file_is_named_anywhere(self):
        self.assertEqual(generate.route_excluded_problems(loader.load_cards()), [])

    def test_a_demoted_skill_in_sources_priority_fails_validate(self):
        cards = loader.load_cards()
        cards["engineering/security"] = dict(cards["engineering/security"],
                                             sources_priority=["files/gstack/cso/SKILL.md"])
        problems = generate.route_excluded_problems(cards)
        self.assertTrue(any("engineering/security" in p and "cso" in p for p in problems), problems)


class TestTrailOfBitsExclusions(unittest.TestCase):
    def test_hooks_workflows_and_commands_never_bundle(self):
        doc = rules.load_rules()
        rules.compile_rules(doc, rules.load_capabilities())
        tob = doc["repos"]["tob"]
        for path in ("plugins/fp-check/hooks/hooks.json", "plugins/static-analysis/workflows/semgrep-scan.js",
                     "plugins/variant-analysis/workflows/variants.js", "plugins/semgrep-rule-creator/commands/semgrep-rule.md",
                     "plugins/sharp-edges/.claude-plugin/plugin.json", "plugins/insecure-defaults/skills/x/SKILL.md",
                     "plugins/variant-analysis/tests/eval.sh"):
            with self.subTest(path):
                self.assertNotIn(rules.classify(tob, path)["decision"], rules.BUNDLED)
        self.assertIn(rules.classify(tob, "plugins/static-analysis/skills/semgrep/SKILL.md")["decision"], rules.BUNDLED)
        self.assertEqual(rules.classify(doc["repos"]["elaya"], "skills/figma-designer/SKILL.md")["decision"], "EXCLUDE")


if __name__ == "__main__":
    unittest.main()
