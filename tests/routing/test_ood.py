"""MP1 F13: out-of-distribution routing — requests no rule was written for (forbid always holds; strict pending)."""
import os
import sys
import unittest

import yaml

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.insert(0, ROOT_DIR)

from agylite.routing import ProjectFacts, Router, capability_ids  # noqa: E402

with open(os.path.join(os.path.dirname(__file__), "ood_scenarios.yaml"), encoding="utf-8") as _f:
    OOD = yaml.safe_load(_f)["scenarios"]


def forbidden(ids, forbid, expected=()):
    """Routed ids that hit a forbid entry (an id, or a domain prefix ending in "/"); expected ids are allowed."""
    return [i for f in forbid for i in ids
            if (i.startswith(f) if f.endswith("/") else i == f) and i not in expected]


class TestOutOfDistribution(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.router = Router()

    def test_at_least_40_scenarios_with_unique_ids(self):
        ids = [sc["id"] for sc in OOD]
        self.assertGreaterEqual(len(ids), 40)
        self.assertEqual(len(ids), len(set(ids)))

    def test_forbid_always_holds(self):
        for sc in OOD:
            with self.subTest(sc["id"]):
                ids = capability_ids(self.router.route(sc["request"], project=ProjectFacts(stage=sc["stage"])))
                self.assertEqual(forbidden(ids, sc.get("forbid", []), sc.get("expect", [])), [],
                                 f"{sc['id']}: routed {ids}")

    def test_expect_holds_unless_pending(self):
        for sc in OOD:
            if not sc.get("expect"):
                continue
            with self.subTest(sc["id"]):
                known = set(self.router.cards)
                ids = set(capability_ids(self.router.route(sc["request"], project=ProjectFacts(stage=sc["stage"]))))
                missing = set(sc["expect"]) - ids
                if sc.get("pending"):
                    # Strict: once every expected capability exists, the marker goes and the expectation is enforced.
                    self.assertFalse(set(sc["expect"]) <= known,
                                     f"{sc['id']}: capabilities exist; remove `pending: {sc['pending']}`")
                    continue
                self.assertEqual(missing, set(), f"{sc['id']}: missing; routed {sorted(ids)}")


if __name__ == "__main__":
    unittest.main()
