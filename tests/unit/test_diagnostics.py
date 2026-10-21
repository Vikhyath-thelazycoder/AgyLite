import contextlib
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.insert(0, ROOT_DIR)

from agylite.diagnostics import benchmark, doctor, validate  # noqa: E402


def quiet(func, *args, **kwargs):
    with contextlib.redirect_stdout(io.StringIO()) as out:
        code = func(*args, **kwargs)
    return code, out.getvalue()


class TestDoctorValidate(unittest.TestCase):
    def test_doctor_passes_on_repo(self):
        code, out = quiet(doctor.run, Path(ROOT_DIR))
        self.assertEqual(code, 0, out)

    def test_validate_passes_on_repo(self):
        code, out = quiet(validate.run, Path(ROOT_DIR), unittests=False)
        self.assertEqual(code, 0, out)

    def test_doctor_detects_mcp_and_missing_version(self):
        with tempfile.TemporaryDirectory() as tmp:
            copy = Path(tmp) / "repo"
            shutil.copytree(ROOT_DIR, copy, ignore=shutil.ignore_patterns(".git", ".staging", "*.egg-info"))
            (copy / "VERSION").unlink()
            (copy / ".mcp.json").write_text("{}", encoding="utf-8")
            code, out = quiet(doctor.run, copy)
        self.assertEqual(code, 1)
        self.assertIn(".mcp.json file exists", out)
        self.assertIn("VERSION file missing", out)


class TestBenchmark(unittest.TestCase):
    def test_measures_fixture_plugin_exactly(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plugin = root / "cache" / "demo"
            (plugin / ".claude-plugin").mkdir(parents=True)
            (plugin / ".claude-plugin" / "plugin.json").write_text(json.dumps({"skills": ["./skills/"]}), encoding="utf-8")
            (plugin / "skills" / "alpha").mkdir(parents=True)
            (plugin / "skills" / "alpha" / "SKILL.md").write_text("---\nname: alpha\ndescription: Does A\n---\nbody", encoding="utf-8")
            (plugin / "agents").mkdir()
            (plugin / "agents" / "helper.md").write_text("# no frontmatter", encoding="utf-8")
            (root / "installed_plugins.json").write_text(json.dumps(
                {"plugins": {"demo@m": [{"installPath": str(plugin), "version": "9.9"}]}}), encoding="utf-8")

            m = benchmark.measure_plugin(plugin)
            self.assertEqual(m["skills"], (1, len("alpha Does A")))
            self.assertEqual(m["agents"], (1, len("helper")))
            self.assertEqual(m["commands"], (0, 0))
            code, out = quiet(benchmark.run, plugins_root=root)
        self.assertEqual(code, 0)
        self.assertIn("| demo@m | 9.9 | 1 | 1 | 0 | 18 |", out)

    def _report(self, old_bytes, new_bytes):
        row = {"id": "x", "capabilities": ["engineering/review"], "routing_ok": True, "old_task": 1, "new_task": 2,
               "old_bytes": old_bytes, "new_bytes": new_bytes}
        return {"routing_accuracy": (1, 1), "bundle": "b", "plugins": [], "old_always": 0, "new_always": 0,
                "own": {}, "l0_bytes": 400, "rows": [row], "route_p50": 0.1, "route_p95": 0.2, "l0_ms": 1,
                "context_p50": 1, "context_p95": 2, "hook_p50": 600, "hook_max": 700}

    def test_totals_say_more_when_new_is_larger(self):
        """IMPLEMENTATION_PLAN §2.1: whole skills can make NEW larger than OLD; the report must say so, not "-96% less"."""
        self.assertIn("(96% more)", benchmark.render(self._report(400, 784)))
        self.assertIn("(50% less)", benchmark.render(self._report(800, 400)))
        self.assertNotIn("-", benchmark.render(self._report(400, 784)).split("Totals over", 1)[1].split("\n", 1)[0])

    def test_reports_tokens_per_message_and_per_task(self):
        """IMPLEMENTATION_PLAN §6 item 5: per message (L0 + hook) and per task (whole skill)."""
        out = benchmark.render(self._report(400, 784))
        self.assertIn("Per message: L0 bootstrap ≈ 100 tokens (once per session) · prompt hook p50 ≈ 150 · max ≈ 175 "
                      "tokens", out)
        self.assertIn("whole primary skill", out)

    def test_no_plugins_is_not_an_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            code, out = quiet(benchmark.run, plugins_root=Path(tmp))
        self.assertEqual(code, 0)
        self.assertIn("No installed plugins", out)


if __name__ == "__main__":
    unittest.main()
