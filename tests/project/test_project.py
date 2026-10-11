"""P10: project state, plan index, reconciliation, decisions, questions, lifecycle, templates and CLI.

Acceptance: state read ≪ full docs (bytes measured); "Add Google Maps navigation to bookings" lands in the existing
booking phase of the one plan with no new mini-plan file (spec §21).
"""
import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.insert(0, ROOT_DIR)

from agylite.cli import main  # noqa: E402
from agylite.events import log as event_log  # noqa: E402
from agylite.project import decisions, lifecycle, plan_index, questions, reconcile, state  # noqa: E402
from agylite.project.identity import detect  # noqa: E402
from agylite.routing import Router  # noqa: E402

PHASES = """
## P2 · Accounts and authentication
Status: COMPLETED · Depends: P1 · Paths: src/auth/** · Flags: security · Evidence: docs/evidence/P2.md
Objective: Travellers sign up and sign in.

| ID | Task | Status | Depends | Capabilities | Security | Design | Testing | Acceptance |
|---|---|---|---|---|---|---|---|---|
| T-2.1 | Email sign-in | COMPLETED | T-1.1 | engineering/security | session cookies | — | auth tests | sign-in works |

## P3 · Booking System
Status: IN_PROGRESS · Depends: P2 · Paths: src/bookings/** · Flags: testing · Evidence: —
Objective: Travellers can book, change and cancel trips.

| ID | Task | Status | Depends | Capabilities | Security | Design | Testing | Acceptance |
|---|---|---|---|---|---|---|---|---|
| T-3.1 | Booking model and API | IN_PROGRESS | T-2.1 | engineering/backend | — | — | API tests | create/cancel booking |
| T-3.2 | Booking confirmation page | PLANNED | T-3.1 | design/frontend | — | layout | UI tests | page shows booking |

## P4 · Payments
Status: PLANNED · Depends: P3 · Paths: src/payments/** · Flags: security · Evidence: —
Objective: Pay for bookings with Stripe.

"""
FILLER = "\n".join(f"Paragraph {i}: " + "realistic project prose about the travel product. " * 12 for i in range(40))


def run_cli(*argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = main(list(argv))
    return code, out.getvalue(), err.getvalue()


class ProjectEnv(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        self.home = base / "home"
        self.root = base / "travel"
        (self.root / "src" / "bookings").mkdir(parents=True)
        (self.root / ".git").mkdir()
        (self.root / ".git" / "HEAD").write_text("ref: refs/heads/main\n")
        (self.root / "package.json").write_text(json.dumps({"dependencies": {"react": "18", "stripe": "1"}}))
        (self.root / "src" / "bookings" / "api.ts").write_text("export const x = 1\n")
        self.env = mock.patch.dict(os.environ, {"AGYLITE_HOME": str(self.home)})
        self.env.start()
        code, _, err = run_cli("project", "init", "--docs", "--project", str(self.root))
        self.assertEqual(code, 0, err)
        plan = self.root / "docs" / "IMPLEMENTATION_PLAN.md"
        plan.write_text(plan.read_text().replace("## Change history", PHASES.lstrip() + "## Change history"))
        self.project = detect(self.root, home=self.home)

    def tearDown(self):
        self.env.stop()
        self.tmp.cleanup()

    def state_and_index(self):
        st = state.require_state(self.project)
        return st, plan_index.load_index(self.project, st)


class TestPlanIndex(ProjectEnv):
    def test_index_fields_and_current_phase(self):
        st, index = self.state_and_index()
        self.assertEqual([p["phase_id"] for p in index["phases"]], ["P1", "P2", "P3", "P4"])
        p3 = plan_index.phase(index, "P3")
        for field in ("phase_id", "phase_name", "status", "active_tasks", "dependencies", "affected_paths",
                      "security_flags", "design_flags", "testing_flags", "last_updated", "evidence_pointer"):
            self.assertIn(field, p3)   # spec §49
        self.assertEqual((p3["status"], p3["active_tasks"], p3["dependencies"]), ("IN_PROGRESS", ["T-3.1"], ["P2"]))
        self.assertTrue(p3["design_flags"] and p3["testing_flags"])
        self.assertEqual(index["current_phase"], "P3")
        self.assertEqual(plan_index.phase(index, "P2")["evidence_pointer"], "docs/evidence/P2.md")
        section = plan_index.phase_section(self.project, st, index, "P3")
        self.assertTrue(section.startswith("## P3 · Booking System") and "T-3.2" in section and "## P4" not in section)

    def test_index_not_rebuilt_when_plan_unchanged(self):
        st, _ = self.state_and_index()
        with mock.patch.object(plan_index, "build_index") as build:
            plan_index.load_index(self.project, st)
        build.assert_not_called()
        plan = self.root / "docs" / "IMPLEMENTATION_PLAN.md"
        plan.write_text(plan.read_text() + "\n")
        self.assertIsNotNone(plan_index.load_index(self.project, st))

    def test_invalid_status_rejected(self):
        with self.assertRaises(plan_index.PlanError):
            plan_index.parse_plan("## P1 · X\nStatus: DONE\n")
        with self.assertRaises(plan_index.PlanError):
            plan_index.parse_plan("## P1 · X\nStatus: PLANNED\n\n| ID | Task | Status |\n|---|---|---|\n| T-1.1 | a | DONE |\n")


class TestReconcile(ProjectEnv):
    def test_google_maps_lands_in_booking_phase_without_new_files(self):
        before = sorted(p.relative_to(self.root).as_posix() for p in self.root.rglob("*") if p.is_file())
        st = state.require_state(self.project)
        report = reconcile.reconcile(self.project, st, Router(), "Add Google Maps navigation to bookings.")
        self.assertEqual(report["status"], "planned")
        self.assertEqual(report["phase"], {"phase_id": "P3", "phase_name": "Booking System"})
        self.assertEqual(report["task"]["id"], "T-3.3")
        self.assertTrue(report["impact"]["security_impact"]["required"])
        self.assertEqual(report["impact"]["affected_phase"], "P3")
        after = sorted(p.relative_to(self.root).as_posix() for p in self.root.rglob("*") if p.is_file())
        self.assertEqual(sorted(set(after) - set(before)), [], "no new (mini-)plan files")
        _, index = self.state_and_index()
        self.assertIn("T-3.3", [t["id"] for t in plan_index.phase(index, "P3")["tasks"]])
        text = (self.root / "docs" / "IMPLEMENTATION_PLAN.md").read_text()
        self.assertIn("T-3.3 added to P3 Booking System", text)
        self.assertEqual(text.count("## P3 ·"), 1)

    def test_impact_has_all_spec_55_fields(self):
        st = state.require_state(self.project)
        imp = reconcile.reconcile(self.project, st, Router(), "Fix the payment webhook security.")["impact"]
        for f in ("affected_domain", "affected_subdomain", "affected_phase", "affected_files", "dependencies",
                  "security_impact", "design_impact", "testing_impact", "performance_impact", "deployment_impact",
                  "documentation_impact", "rollback_impact"):
            self.assertIn(f, imp)
        self.assertEqual(imp["affected_phase"], "P4")

    def test_unmatched_request_needs_phase_then_new_phase(self):
        st = state.require_state(self.project)
        report = reconcile.reconcile(self.project, st, Router(), "Add a loyalty points programme")
        self.assertEqual(report["status"], "needs_phase")
        report = reconcile.reconcile(self.project, st, Router(), "Add a loyalty points programme",
                                     new_phase="Loyalty programme")
        self.assertEqual((report["phase"]["phase_id"], report["task"]["id"]), ("P5", "T-5.1"))

    def test_task_added_to_completed_phase_reopens_it(self):
        st, index = self.state_and_index()
        _, reopened = reconcile.add_task(self.project, st, index, "P2", "Add passkey sign-in")
        self.assertTrue(reopened)
        self.assertEqual(plan_index.phase(plan_index.load_index(self.project, st), "P2")["status"], "IN_PROGRESS")

    def test_status_transitions_and_evidence(self):
        st, index = self.state_and_index()
        with self.assertRaises(lifecycle.TransitionError):
            reconcile.set_status(self.project, st, index, "T-3.2", "COMPLETED", "x")   # PLANNED → COMPLETED
        with self.assertRaises(lifecycle.TransitionError):
            reconcile.set_status(self.project, st, index, "T-3.1", "DONE")
        reconcile.set_status(self.project, st, index, "T-3.1", "READY_FOR_VERIFICATION")
        index = plan_index.load_index(self.project, st)
        with self.assertRaises(lifecycle.TransitionError):
            reconcile.set_status(self.project, st, index, "T-3.1", "VERIFIED")        # no evidence
        reconcile.set_status(self.project, st, index, "T-3.1", "VERIFIED", "tests/booking: 12 passed")
        index = plan_index.load_index(self.project, st)
        self.assertEqual(plan_index.phase(index, "P3")["tasks"][0]["status"], "VERIFIED")
        last = state.require_state(self.project)["verification"]["last"]
        self.assertEqual((last["task"], last["result"]), ("T-3.1", "VERIFIED"))
        reconcile.set_status(self.project, st, index, "P4", "IN_PROGRESS")
        self.assertEqual(plan_index.phase(plan_index.load_index(self.project, st), "P4")["status"], "IN_PROGRESS")


class TestStateCost(ProjectEnv):
    def test_state_read_much_smaller_than_docs(self):
        docs = self.root / "docs"
        for name in ("PRD.md", "TRD.md", "ARCHITECTURE.md", "SECURITY.md", "DESIGN.md", "SYSTEM_WORKFLOW.md", "FEATURES.md"):
            (docs / name).write_text((docs / name).read_text() + FILLER)
        st, index = self.state_and_index()
        state_bytes = sum((self.project.state_dir / f).stat().st_size for f in ("state.yaml", "plan-index.yaml"))
        doc_bytes = sum(p.stat().st_size for p in docs.glob("*.md"))
        self.assertLess(state_bytes * 5, doc_bytes, f"state {state_bytes} B vs docs {doc_bytes} B")
        lines = state.summary_lines(st, index)
        self.assertLess(len("\n".join(lines).encode()), 600)
        self.assertIn("phase P3 Booking System (IN_PROGRESS) · active tasks: T-3.1", lines)


class TestDecisionsAndQuestions(ProjectEnv):
    def test_decisions_supersede_relevance_and_render(self):
        d1 = decisions.add(self.project, kind="security", topic="API keys",
                           decision="All private API keys remain server-side.", reason="Client keys leak")
        decisions.add(self.project, kind="design", topic="Visual direction", decision="Minimal editorial, no gradients",
                      reason="Brand")
        d3 = decisions.add(self.project, kind="architecture", topic="Queue", decision="Use Postgres queue",
                           reason="One datastore")
        d4 = decisions.add(self.project, kind="architecture", topic="Queue", decision="Use Redis streams",
                           reason="Throughput", supersedes=d3["decision_id"])
        self.assertEqual((d1["decision_id"], d4["decision_id"], d4["supersedes"]), ("D-001", "D-004", "D-003"))
        self.assertEqual([d["decision_id"] for d in decisions.find(self.project, kind="architecture")], ["D-004"])

        def ids(caps):
            return [d["decision_id"] for d in decisions.relevant(self.project, caps)]
        self.assertEqual(ids(["design/visual-quality"]), ["D-002"])
        self.assertEqual(ids(["engineering/security", "codebase/impact-analysis"]), ["D-001", "D-004"])
        self.assertEqual(ids(["seo/auditing"]), [])
        md = (self.root / "docs" / "PROJECT_DECISIONS.md").read_text()
        self.assertIn("| D-003 | ", md)
        self.assertIn("SUPERSEDED", md)
        with self.assertRaises(decisions.DecisionError):
            decisions.add(self.project, kind="vibes", topic="x", decision="y", reason="z")

    def test_question_priorities_inference_and_answers(self):
        bank = questions.load_bank()
        self.assertEqual(questions.validate_bank(bank), [])
        ask, skipped = questions.next_questions(bank, "Build me a travel booking SaaS with AI trip planning",
                                                stage="new", stack=["react", "stripe"])
        self.assertEqual({q["priority"] for q in ask}, {"BLOCKING"})
        self.assertIn("product-goal", [q["id"] for q in ask])
        self.assertEqual(skipped["frontend"], "inferred from the project (react)")
        self.assertIn("deferred", skipped["analytics"])
        answers = {q["id"]: "x" for q in ask}
        ask2, _ = questions.next_questions(bank, "Build me a travel booking SaaS with AI trip planning", stage="new",
                                           stack=["react", "stripe"], answers=answers)
        self.assertTrue(ask2 and "BLOCKING" not in {q["priority"] for q in ask2})
        self.assertIn("ai", [q["id"] for q in ask2])
        ask3, _ = questions.next_questions(bank, "Fix the typo in the footer", stage="existing")
        self.assertEqual(ask3, [])


class TestLifecycle(unittest.TestCase):
    def test_stage_and_stack_detection(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertEqual(lifecycle.detect_stage(root), "new")
            (root / "requirements.txt").write_text("Django==5.0\npsycopg2\n")
            self.assertEqual(lifecycle.detect_stage(root), "existing")
            self.assertEqual(lifecycle.detect_stack(root), ["python", "django", "postgres"])
            self.assertEqual(lifecycle.detect_stage(root, {"project": {"stage": "new"}}), "new")

    def test_completion_states_are_spec_25(self):
        self.assertEqual(len(lifecycle.COMPLETION_STATES), 9)
        self.assertNotIn("DONE", lifecycle.COMPLETION_STATES)


class TestTemplates(unittest.TestCase):
    REQUIRED = {
        "PRD.md": ["Problem", "Target users", "Goals", "Non-goals", "Features", "Workflows", "Constraints",
                   "Success criteria", "Assumptions", "Open questions"],
        "TRD.md": ["Stack", "Architecture", "Infrastructure", "APIs", "Database", "Integrations", "AI/LLM system",
                   "Runtime", "Deployment", "Environment variables", "Dependencies"],
        "ARCHITECTURE.md": ["Major components", "Boundaries", "Data flow", "Trust boundaries", "Integrations",
                            "Infrastructure", "Failure modes"],
        "SYSTEM_WORKFLOW.md": ["User action", "Backend behavior", "Data flow", "AI flow", "External API flow",
                               "State changes", "Verification"],
        "SECURITY.md": ["Assets and threats", "Secrets", "Security tests"],
        "DESIGN.md": ["Visual direction", "Component principles", "Typography", "Color", "Spacing", "Responsive rules",
                      "Interaction", "Accessibility", "Motion", "Reference sources"],
        "FEATURES.md": ["Feature list"],
        "IMPLEMENTATION_PLAN.md": ["P1 · Foundations", "Change history"],
        "PROJECT_DECISIONS.md": [],
    }

    def test_templates_have_spec_20_sections(self):
        base = Path(ROOT_DIR) / "templates" / "project-docs"
        self.assertEqual(sorted(p.name for p in base.glob("*.md")), sorted(self.REQUIRED))
        for name, headings in self.REQUIRED.items():
            text = (base / name).read_text(encoding="utf-8")
            for h in headings:
                self.assertIn(f"\n## {h}\n", text, f"{name}: ## {h}")
            self.assertIn("{{PROJECT_NAME}}", text)
        plan = (base / "IMPLEMENTATION_PLAN.md").read_text(encoding="utf-8")
        self.assertEqual(plan_index.parse_plan(plan)[0]["phase_id"], "P1")
        self.assertIn(decisions.MARK_START, (base / "PROJECT_DECISIONS.md").read_text(encoding="utf-8"))


class TestCli(ProjectEnv):
    def test_cli_flow(self):
        p = ("--project", str(self.root))
        code, out, _ = run_cli("plan", "reconcile", "Add", "Google", "Maps", "navigation", "to", "bookings", *p)
        self.assertEqual(code, 0)
        self.assertIn("phase_id: P3", out)
        self.assertEqual(run_cli("plan", "set-status", "T-3.2", "IN_PROGRESS", *p)[0], 0)
        code, _, err = run_cli("plan", "set-status", "T-3.2", "COMPLETED", *p)
        self.assertEqual(code, 1)
        self.assertIn("not allowed", err)
        code, out, _ = run_cli("state", *p, "--json")
        self.assertEqual(json.loads(out)["current_phase"]["active_tasks"], ["T-3.1", "T-3.2"])
        self.assertEqual(run_cli("decide", "add", "--kind", "security", "--topic", "Keys", "--decision", "Server-side",
                                 "--reason", "Leaks", *p)[0], 0)
        code, out, _ = run_cli("context", "engineering/security", "--level", "1", *p)
        self.assertIn("D-001 [security] Keys: Server-side", out)
        code, out, _ = run_cli("bootstrap", "--session", "s1", *p)
        self.assertIn("phase: P3 Booking System (IN_PROGRESS)", out)
        self.assertIn("plan: docs/IMPLEMENTATION_PLAN.md#P3", out)
        self.assertTrue((self.project.data_dir / "sessions" / "s1" / "session.yaml").is_file())
        self.assertEqual(run_cli("project", "init", *p)[0], 1)    # already initialised

    def test_relink_moves_data_without_merging(self):
        run_cli("bootstrap", "--session", "s1", "--project", str(self.root))
        old_id = self.project.project_id
        moved = self.root.parent / "travel-moved"
        self.root.rename(moved)
        new = detect(moved, home=self.home)
        self.assertNotEqual(new.project_id, old_id)
        code, _, err = run_cli("project", "relink", "--from", old_id, "--project", str(moved))
        self.assertEqual(code, 0, err)
        self.assertTrue((new.data_dir / "sessions" / "s1" / "session.yaml").is_file())
        self.assertFalse((self.home / "projects" / old_id).exists())
        self.assertEqual(state.require_state(new)["project"]["project_id"], new.project_id)
        self.assertIn(old_id, state.read_yaml(new.data_dir / "project.yaml")["aliases"])


class TestVerificationPolicyState(ProjectEnv):
    """D-035: state records the global local-test-first policy; browser exceptions stay in their own project."""

    def test_state_records_policy_and_evidence(self):
        ver = state.require_state(self.project)["verification"]
        self.assertEqual((ver["mode"], ver["browser_visual_verification"], ver["chrome_devtools"],
                          ver["screenshot_verification"]), ("local-test-first", "disabled", "disabled", "disabled"))
        state.record_verification(self.project, "T-3.1", "PASSED", "python -m unittest: 12 passed")
        ver = state.require_state(self.project)["verification"]
        self.assertEqual((ver["mode"], ver["last"]["evidence"]), ("local-test-first", "python -m unittest: 12 passed"))
        self.assertIn("verification: local-test-first (no browser/Chrome DevTools/screenshots)",
                      state.summary_lines(state.require_state(self.project)))

    def test_browser_exception_is_logged_per_project(self):
        other_root = self.root.parent / "shop"
        (other_root / ".git").mkdir(parents=True)
        (other_root / ".git" / "HEAD").write_text("ref: refs/heads/main\n")
        self.assertEqual(run_cli("project", "init", "--project", str(other_root))[0], 0)
        other = detect(other_root, home=self.home)
        with self.assertRaises(state.StateError):
            state.record_browser_exception(self.project, "  ")
        state.record_browser_exception(self.project, "canvas chart rendering has no DOM to assert on")
        mine = state.read_yaml(self.project.state_dir / state.VERIFICATION_FILE)
        self.assertEqual(len(mine["browser_exceptions"]), 1)
        self.assertFalse(mine["browser_exceptions"][0]["screenshots_in_context"])
        theirs = state.read_yaml(other.state_dir / state.VERIFICATION_FILE) or {}
        self.assertNotIn("browser_exceptions", theirs)
        events = [e["event"] for e in event_log.read(self.project)]
        self.assertIn("BROWSER_EXCEPTION_REQUESTED", events)
        self.assertNotIn("BROWSER_EXCEPTION_REQUESTED", [e["event"] for e in event_log.read(other)])



class TestTrialFixes(ProjectEnv):
    """Gaps found by the 2026-10-11 hands-on trial (docs/TRY_AGYLITE.md)."""

    def plan_text(self):
        return (self.root / "docs" / "IMPLEMENTATION_PLAN.md").read_text(encoding="utf-8")

    def test_task_status_rolls_up_into_the_phase_and_state(self):
        p = ("--project", str(self.root))
        for item, status, *ev in (("T-3.1", "READY_FOR_VERIFICATION"), ("T-3.1", "VERIFIED", "e1.json"),
                                  ("T-3.2", "IN_PROGRESS"), ("T-3.2", "READY_FOR_VERIFICATION")):
            code, _, err = run_cli("plan", "set-status", item, status, *(["--evidence", ev[0]] if ev else []), *p)
            self.assertEqual(code, 0, err)
        st, index = self.state_and_index()
        self.assertEqual(plan_index.phase(index, "P3")["status"], "IN_PROGRESS")   # one task still open
        self.assertEqual(run_cli("plan", "set-status", "T-3.2", "VERIFIED", "--evidence", "e2.json", *p)[0], 0)
        st, index = self.state_and_index()
        p3 = plan_index.phase(index, "P3")
        self.assertEqual((p3["status"], p3["evidence_pointer"]), ("VERIFIED", "e2.json"))
        self.assertIn("P3: IN_PROGRESS → VERIFIED (roll-up from T-3.2)", self.plan_text())
        self.assertEqual(st["plan"]["current_phase"], index["current_phase"])
        self.assertEqual(st["verification"]["last_task"]["task"], "T-3.2")
        # A later plain verify run does not erase which task was last verified.
        state.record_verification(self.project, None, "PASSED", "e3.json")
        st = state.require_state(self.project)
        self.assertEqual((st["verification"]["last"]["task"], st["verification"]["last_task"]["task"]), (None, "T-3.2"))
        # Reopening a verified task reopens its phase.
        self.assertEqual(run_cli("plan", "set-status", "T-3.2", "IN_PROGRESS", *p)[0], 0)
        self.assertEqual(plan_index.phase(self.state_and_index()[1], "P3")["status"], "IN_PROGRESS")

    def test_first_started_task_starts_a_planned_phase(self):
        p = ("--project", str(self.root))
        self.assertEqual(run_cli("plan", "add-task", "P1", "Skeleton", *p)[1].strip(), "T-1.1 added to P1")
        self.assertEqual(run_cli("plan", "set-status", "T-1.1", "IN_PROGRESS", *p)[0], 0)
        self.assertEqual(plan_index.phase(self.state_and_index()[1], "P1")["status"], "IN_PROGRESS")

    def test_blocking_questions_must_be_answered_before_a_task_starts(self):
        p = ("--project", str(self.root))
        code, out, _ = run_cli("project", "questions", "add", "login", "for", "users", *p, "--json")
        self.assertIn("auth", [q["id"] for q in json.loads(out)["ask"] if q["priority"] == "BLOCKING"])
        code, _, err = run_cli("plan", "set-status", "T-3.2", "IN_PROGRESS", *p)
        self.assertEqual(code, 3)
        self.assertIn("auth", err)
        self.assertIn("unanswered BLOCKING questions: auth", "\n".join(state.summary_lines(state.require_state(self.project))))
        self.assertEqual(run_cli("project", "answer", "auth", "email", "and", "password", *p)[0], 0)
        code, _, err = run_cli("plan", "set-status", "T-3.2", "IN_PROGRESS", *p)
        self.assertEqual(code, 0, err)
        self.assertEqual(state.require_state(self.project)["pending_questions"], [])

    def test_verify_ties_a_run_to_the_single_active_task(self):
        from agylite.verify.engine import active_task
        self.assertEqual(active_task(self.project), "T-3.1")
        run_cli("plan", "set-status", "T-3.2", "IN_PROGRESS", "--project", str(self.root))
        self.assertIsNone(active_task(self.project))                      # two active: not guessed


class TestChangedFiles(unittest.TestCase):
    def test_os_state_is_not_a_code_change(self):
        import shutil
        import subprocess
        from agylite.codebase.impact import changed_files
        if not shutil.which("git"):
            self.skipTest("git not installed")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            (root / ".agylite" / "evidence").mkdir(parents=True)
            (root / ".agylite" / "state.yaml").write_text("x: 1\n")
            (root / ".agylite" / "evidence" / "e.json").write_text("{}")
            (root / "todo.py").write_text("print(1)\n")
            self.assertEqual(changed_files(root), ["todo.py"])

if __name__ == "__main__":
    unittest.main()
