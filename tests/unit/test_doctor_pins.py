"""MP1 F9: doctor's pin-age warning follows each upstream's tracking policy."""
import json
import os
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.insert(0, ROOT_DIR)

from agylite.diagnostics.doctor import fresh_dates, last_update_run, pin_age_lines  # noqa: E402

TODAY = date(2026, 10, 21)
POLICY = {"ecc": {"track": "weekly"}, "addy": {"track": "weekly"}, "brag": {"track": "monthly"},
          "taste": {"track": "manual"}}


class TestPinAges(unittest.TestCase):
    def test_threshold_depends_on_track(self):
        dates = {"ecc": date(2026, 10, 3), "addy": date(2026, 10, 15), "brag": date(2026, 10, 3),
                 "taste": date(2026, 1, 1)}
        lines = dict((msg.split(" ")[0], (lvl, msg)) for lvl, msg in pin_age_lines(dates, POLICY, TODAY))
        self.assertEqual(lines["weekly"][0], "warn")            # 18 days > 14
        self.assertIn("oldest ecc, 18 days", lines["weekly"][1])
        self.assertIn("review ecc with", lines["weekly"][1])    # addy (6 days) is not listed
        self.assertEqual(lines["monthly"][0], "ok")             # 18 days ≤ 45
        self.assertEqual(lines["manual"][0], "ok")              # never due, however old

    def test_a_check_that_found_the_pin_current_refreshes_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            (home / "updates").mkdir()
            (home / "updates" / "tracking.json").write_text(json.dumps(
                {"ecc": {"applied_check": "2026-10-20T09:00:00+00:00"}}))
            dates = fresh_dates({"ecc": date(2026, 10, 3), "addy": date(2026, 10, 3)}, home)
            self.assertEqual(dates, {"ecc": date(2026, 10, 20), "addy": date(2026, 10, 3)})
            self.assertEqual(last_update_run(home), "2026-10-20")
            self.assertIsNone(last_update_run(home / "nothing"))


class TestSkillOwnedCopies(unittest.TestCase):
    def test_reference_linked_by_its_own_skill_is_not_a_duplicate(self):
        """MP1 F12: UI/UX Pro Max ships banner-sizes-and-styles.md in both `design` and `banner-design`; each
        SKILL.md links its own copy, so both stay (whole skills) and doctor does not warn."""
        from agylite.diagnostics.doctor import skill_owned_copy
        with tempfile.TemporaryDirectory() as tmp:
            b = Path(tmp)
            for skill, links in (("design", True), ("banner-design", True), ("other", False)):
                d = b / "files" / "ux" / skill / "references"
                d.mkdir(parents=True)
                (d / "sizes.md").write_text("same\n")
                (d.parent / "SKILL.md").write_text("Read `references/sizes.md`.\n" if links else "nothing\n")
            self.assertTrue(skill_owned_copy(b, "files/ux/design/references/sizes.md"))
            self.assertTrue(skill_owned_copy(b, "files/ux/banner-design/references/sizes.md"))
            self.assertFalse(skill_owned_copy(b, "files/ux/other/references/sizes.md"))
            self.assertFalse(skill_owned_copy(b, "files/ux/design/SKILL.md"))


if __name__ == "__main__":
    unittest.main()
