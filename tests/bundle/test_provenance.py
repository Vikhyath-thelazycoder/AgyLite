import os
import sys
import unittest

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.insert(0, ROOT_DIR)

from agylite.bundle import provenance, rules  # noqa: E402

def _expected_bundled_files():
    """Bundled files per the generated extraction summary (COPY + ADAPT + PRESERVE + GENERATED, MP3 §2.1). Upstream updates (P28) change the
    number; these tests check that provenance, registry and licenses all agree with the audited extraction matrix."""
    import json as _json
    with open(os.path.join(ROOT_DIR, "docs", "audit", "evidence", "extraction-summary.json"), encoding="utf-8") as f:
        repos = _json.load(f)["repos"]
    return sum(d.get(k, {}).get("files", 0) for d in repos.values() for k in ("COPY", "ADAPT", "PRESERVE", "GENERATED"))


EXPECTED_BUNDLED_FILES = _expected_bundled_files()


class TestPlannedProvenance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.records = provenance.planned_records(verified_on="2026-10-03")
        cls.caps = rules.load_capabilities()

    def test_one_record_per_bundled_file(self):
        self.assertEqual(len(self.records), EXPECTED_BUNDLED_FILES)

    def test_records_validate(self):
        self.assertEqual(provenance.validate(self.records, self.caps), [])

    def test_original_hash_matches_audited_inventory(self):
        evidence = rules.evidence_dir()
        by_repo = {}
        for r in self.records[:: max(1, len(self.records) // 200)]:
            repo = r["destination_path"].split("/")[2]
            inv = by_repo.setdefault(repo, {p: sha for p, _, sha in rules.read_inventory(evidence, repo)})
            self.assertEqual(r["original_hash"], inv[r["source_path"]])

    def test_commit_pins_match_snapshot(self):
        pins = {p["repo"]: p["head"] for p in provenance.load_pins().values()}
        for r in self.records:
            self.assertEqual(r["commit_sha"], pins[r["repository"]])

    def test_validator_rejects_bad_records(self):
        bad = dict(self.records[0], original_hash="xyz", license="", integration_type="EXCLUDE")
        problems = provenance.validate([bad, dict(self.records[0])] + [self.records[0]], self.caps)
        joined = " ".join(problems)
        self.assertIn("original_hash", joined)
        self.assertIn("license/attribution empty", joined)
        self.assertIn("not a bundled decision", joined)
        self.assertIn("duplicate destination_path", joined)
        self.assertTrue(provenance.validate([self.records[0]], self.caps, require_bundled_hash=True))


class TestLicenses(unittest.TestCase):
    def test_every_upstream_has_license_and_attribution(self):
        data = provenance.load_licenses()
        self.assertEqual(sorted(data), sorted(provenance.load_pins()))
        for repo, info in data.items():
            self.assertIn(info["license"], {"MIT", "Apache-2.0"}, repo)
            self.assertTrue(info["attribution"], repo)
            self.assertTrue(info["license_files"] or info["note"], repo)
        self.assertEqual(sum(v["bundled_files"] for v in data.values()), EXPECTED_BUNDLED_FILES)

    def test_notices_file_lists_every_upstream(self):
        with open(os.path.join(ROOT_DIR, "THIRD_PARTY_NOTICES.md"), encoding="utf-8") as f:
            text = f.read()
        for info in provenance.load_licenses().values():
            self.assertIn(info["repository"], text)


if __name__ == "__main__":
    unittest.main()
