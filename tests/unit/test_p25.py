"""P25: doctor host/supply checks (fixture user home), redacted diagnostics, absolute-import closure, benchmark."""
import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.insert(0, ROOT_DIR)

from agylite.bundle.closure import references, resolve  # noqa: E402
from agylite.diagnostics import benchmark, doctor  # noqa: E402


def fake_plugin(user: Path, name: str, version: str, mcp=None):
    path = user / "plugin-cache" / name
    (path / "skills" / "demo").mkdir(parents=True)
    (path / "skills" / "demo" / "SKILL.md").write_text("---\nname: demo\ndescription: " + "x" * 400 + "\n---\n",
                                                        encoding="utf-8")
    if mcp:
        (path / ".mcp.json").write_text(json.dumps({"mcpServers": mcp}), encoding="utf-8")
    reg = user / ".claude" / "plugins" / "installed_plugins.json"
    reg.parent.mkdir(parents=True, exist_ok=True)
    data = json.loads(reg.read_text(encoding="utf-8")) if reg.is_file() else {"version": 2, "plugins": {}}
    data["plugins"][name] = [{"version": version, "installPath": str(path)}]
    reg.write_text(json.dumps(data), encoding="utf-8")


class TestDoctorHost(unittest.TestCase):
    def test_reports_separate_plugins_mcp_and_redacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            user = Path(tmp)
            fake_plugin(user, "ecc@ecc", "2.2.3", {"chrome-devtools": {"command": "npx"}, "memory": {}})
            fake_plugin(user, "leaky@x", "ghp_" + "a" * 36)          # a secret-looking value must not be printed
            (user / ".claude.json").write_text(json.dumps({"mcpServers": {"github": {"env": {"TOKEN": "s3cret"}}}}),
                                               encoding="utf-8")
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = doctor.run(Path(ROOT_DIR), user_home=user)
            text = out.getvalue()
        self.assertEqual(code, 0)
        self.assertIn("ecc@ecc 2.2.3 is installed separately", text)
        self.assertIn("host MCP server 'chrome-devtools' enabled by plugin ecc@ecc — browser automation", text)
        self.assertIn("host MCP server 'github' configured in ~/.claude.json", text)
        self.assertNotIn("ghp_" + "a" * 36, text)
        self.assertNotIn("s3cret", text)


class TestClosureAbsoluteImports(unittest.TestCase):
    def test_function_local_absolute_import_resolves(self):
        text = "def run():\n    from graphify.serve import _query_graph_text\n    import networkx.readwrite\n"
        refs = references(text, "graphify/cli.py")
        files = {"graphify/cli.py", "graphify/serve.py", "graphify/__init__.py"}
        dirs = {"graphify"}
        resolved = {resolve(r, "graphify/cli.py", files, dirs) for r in refs}
        self.assertIn("graphify/serve.py", resolved)
        self.assertIsNone(resolve("pyabs:networkx/readwrite", "graphify/cli.py", files, dirs))


class TestBenchmark(unittest.TestCase):
    def test_compare_reports_routing_and_lower_new_baseline(self):
        with tempfile.TemporaryDirectory() as tmp:
            user = Path(tmp)
            fake_plugin(user, "ecc@ecc", "2.2.3")
            r = benchmark.compare(user / ".claude" / "plugins", repeats=2)
            md = benchmark.render(r)
        ok, total = r["routing_accuracy"]
        self.assertEqual(ok, total)
        self.assertGreater(total, 15)
        # MP3 §2.2 + §6.4: L0 carries the Ponytail lite ruleset (≈ 2.9 KB) on every turn, so the per-turn ceiling
        # rose from 6,000 to 8,000 bytes (≈ 1,500 → 2,000 est. tokens).
        self.assertLess(r["new_always"], 8000)
        self.assertIn("Routing accuracy on the spec scenarios", md)
        self.assertIn("estimates", md)


if __name__ == "__main__":
    unittest.main()
