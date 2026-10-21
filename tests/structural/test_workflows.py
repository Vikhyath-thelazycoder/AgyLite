"""MP1 F14: GitHub rejects a workflow that uses the `runner` context in workflow- or job-level `env` (0 jobs, never
scheduled). A cheap guard that works without actionlint."""
import os
import unittest
from pathlib import Path

import yaml

ROOT = Path(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
WORKFLOWS = sorted((ROOT / ".github" / "workflows").glob("*.yml"))


def _runner_in(env) -> list:
    return [k for k, v in (env or {}).items() if "runner." in str(v)]


class TestWorkflows(unittest.TestCase):
    def test_no_runner_context_in_workflow_or_job_env(self):
        self.assertTrue(WORKFLOWS)
        for path in WORKFLOWS:
            with self.subTest(path.name):
                doc = yaml.safe_load(path.read_text(encoding="utf-8"))
                self.assertEqual(_runner_in(doc.get("env")), [], f"{path.name}: workflow-level env")
                for name, job in (doc.get("jobs") or {}).items():
                    self.assertEqual(_runner_in(job.get("env")), [], f"{path.name}: jobs.{name}.env")

    def test_ci_lints_every_workflow(self):
        ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
        self.assertIn("actionlint-py==", ci)    # pinned exact version
        self.assertIn("actionlint .github/workflows/*.yml", ci)


class TestDoctorWorkflowCheck(unittest.TestCase):
    def run_check(self, which):
        import contextlib
        import io
        from unittest import mock

        from agylite.diagnostics import Report
        from agylite.diagnostics.doctor import workflow_checks
        with contextlib.redirect_stdout(io.StringIO()) as out, mock.patch("shutil.which", return_value=which):
            r = Report("t")
            workflow_checks(r, ROOT)
        return r, out.getvalue()

    def test_without_actionlint_it_warns_instead_of_passing(self):
        r, out = self.run_check(None)
        self.assertEqual((r.failed, r.warned), (0, 1))
        self.assertIn("actionlint not installed: expression contexts not checked", out)

    def test_every_workflow_is_parsed(self):
        _r, out = self.run_check(None)
        for path in WORKFLOWS:
            self.assertIn(f".github/workflows/{path.name} valid YAML workflow", out)

if __name__ == "__main__":
    unittest.main()
