"""P11: concurrent sessions on the same project lose no update and never expose a partial file (doc 14 §7)."""
import os
import subprocess
import sys
import tempfile
import textwrap
import threading
import time
import unittest
from pathlib import Path

import yaml

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.insert(0, ROOT_DIR)

from tests.context.fixtures import make_project  # noqa: E402
from agylite.isolation import LockTimeout, project_lock  # noqa: E402
from agylite.project import plan_index, state  # noqa: E402
from agylite.project.identity import detect  # noqa: E402

WORKER = textwrap.dedent("""
    import sys
    from pathlib import Path
    sys.path.insert(0, {root!r})
    from agylite.project.identity import detect
    from agylite.project import state, reconcile
    ref = detect(Path(sys.argv[1]), home=Path(sys.argv[2]))
    mode, n = sys.argv[3], int(sys.argv[4])
    for i in range(n):
        if mode == "counter":
            state.update_state(ref, lambda s: s["answers"].__setitem__("counter", int(s["answers"].get("counter", 0)) + 1))
        else:
            reconcile.add_task(ref, state.require_state(ref), None, "P1", f"task from {{sys.argv[5]}} #{{i}}")
""").format(root=ROOT_DIR)


class TestConcurrency(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        self.home = base / "home"
        self.root = make_project(base)
        self.ref = detect(self.root, home=self.home)
        state.save_state(self.ref, state.new_state(self.ref, "existing"))
        plan = self.root / "docs" / "IMPLEMENTATION_PLAN.md"
        plan.parent.mkdir()
        plan.write_text((Path(ROOT_DIR) / "templates" / "project-docs" / "IMPLEMENTATION_PLAN.md").read_text())
        self.worker = base / "worker.py"
        self.worker.write_text(WORKER)

    def tearDown(self):
        self.tmp.cleanup()

    def spawn(self, mode, n, tag="w"):
        return subprocess.Popen([sys.executable, str(self.worker), str(self.root), str(self.home), mode, str(n), tag],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def wait_all(self, procs):
        for p in procs:
            _, err = p.communicate(timeout=120)
            self.assertEqual(p.returncode, 0, err.decode())

    def test_no_lost_updates_across_processes(self):
        self.wait_all([self.spawn("counter", 25) for _ in range(4)])
        self.assertEqual(state.require_state(self.ref)["answers"]["counter"], 100)

    def test_concurrent_plan_edits_keep_unique_task_ids(self):
        self.wait_all([self.spawn("tasks", 5, tag=f"p{i}") for i in range(3)])
        index = plan_index.load_index(self.ref, state.require_state(self.ref), rebuild=True)
        ids = [t["id"] for t in plan_index.phase(index, "P1")["tasks"]]
        self.assertEqual(len(ids), 15)                     # the template's P1 starts empty; 15 added
        self.assertEqual(len(set(ids)), 15, ids)
        text = (self.root / "docs" / "IMPLEMENTATION_PLAN.md").read_text()
        self.assertEqual(text.count(" added to P1 Foundations"), 15)

    def test_readers_never_see_a_partial_file(self):
        big = {f"k{i}": "x" * 200 for i in range(300)}
        stop, errors = threading.Event(), []

        def writer():
            while not stop.is_set():
                state.update_state(self.ref, lambda s: s["answers"].update(big))

        t = threading.Thread(target=writer)
        t.start()
        try:
            for _ in range(300):
                try:
                    data = yaml.safe_load(state.state_path(self.ref).read_text())
                    if not isinstance(data, dict) or "project" not in data:
                        errors.append("incomplete document")
                except yaml.YAMLError as exc:
                    errors.append(str(exc))
        finally:
            stop.set()
            t.join()
        self.assertEqual(errors, [])
        self.assertEqual([p.name for p in self.ref.state_dir.iterdir() if p.name.endswith(".tmp")], [])

    def test_lock_timeout_and_per_project_independence(self):
        other = detect(make_project(Path(self.tmp.name), "other"), home=self.home)
        held, release = threading.Event(), threading.Event()

        def hold():
            with project_lock(self.ref, "state"):
                held.set()
                release.wait(5)

        t = threading.Thread(target=hold)
        t.start()
        held.wait(5)
        try:
            start = time.monotonic()
            with self.assertRaises(LockTimeout):
                with project_lock(self.ref, "state", timeout=0.2):
                    pass
            self.assertLess(time.monotonic() - start, 2)
            with project_lock(other, "state", timeout=0.2):   # another project never waits on this one
                pass
            with project_lock(self.ref, "plan", timeout=0.2):  # different lock names are independent
                pass
        finally:
            release.set()
            t.join()

    def test_lock_is_reentrant_in_one_thread(self):
        with project_lock(self.ref, "state", timeout=0.2):
            with project_lock(self.ref, "state", timeout=0.2):
                state.update_state(self.ref, lambda s: s["answers"].__setitem__("nested", "ok"))
        self.assertEqual(state.require_state(self.ref)["answers"]["nested"], "ok")


if __name__ == "__main__":
    unittest.main()
