"""Plan B breadth (IMPLEMENTATION_PLAN §2.1): the skill catalog keeps one canonical copy per (upstream, name), skips
translations and host ports, flags policy-violating skills, ranks with BM25, and fetches one folder at its pin."""
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.insert(0, ROOT_DIR)

from agylite import catalog  # noqa: E402
from agylite.bundle.store import git_blob_sha1  # noqa: E402

SWIFT = "---\nname: swiftui-patterns\ndescription: SwiftUI view composition, state and navigation patterns\n---\n# SwiftUI\nSee [refs](references/state.md).\n"
SWIFT_JA = "---\nname: swiftui-patterns\ndescription: SwiftUI のパターン\n---\n# SwiftUI\n"
SWIFT_OLD = "---\nname: swiftui-patterns\ndescription: SwiftUI patterns (older, shorter copy)\n---\n# SwiftUI\n"
GO = "---\nname: golang-patterns\ndescription: Idiomatic Go error handling and packages\n---\n# Go\n"
MCP = "---\nname: linear-sync\ndescription: Sync tickets to Linear through its MCP server\n---\n# Linear\n"
FILES = {
    "skills/swiftui-patterns/SKILL.md": SWIFT, "skills/swiftui-patterns/references/state.md": "# State\n",
    "docs/ja-JP/skills/swiftui-patterns/SKILL.md": SWIFT_JA, ".kiro/skills/swiftui-patterns/SKILL.md": SWIFT_OLD,
    "legacy/swiftui-patterns/SKILL.md": SWIFT_OLD, "skills/golang-patterns/SKILL.md": GO,
    "skills/linear-sync/SKILL.md": MCP, "skills/linear-sync/.mcp.json": "{}", "README.md": "# ecc\n"}


def git(*a, cwd):
    return subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t", *a], cwd=cwd, check=True,
                          capture_output=True, text=True).stdout.strip()


class Fixture(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        self.upstream = base / "remote" / "affaan-m" / "ECC.git"
        self.upstream.mkdir(parents=True)
        git("init", "-q", "-b", "main", cwd=self.upstream)
        for rel, text in FILES.items():
            (self.upstream / rel).parent.mkdir(parents=True, exist_ok=True)
            (self.upstream / rel).write_text(text, encoding="utf-8")
        git("add", "-A", cwd=self.upstream)
        git("commit", "-q", "-m", "x", cwd=self.upstream)
        self.sha = git("rev-parse", "HEAD", cwd=self.upstream)
        self.staging = base / "staging"
        self.staging.mkdir()
        (self.staging / "ecc").symlink_to(self.upstream)
        self.evidence = base / "evidence"
        (self.evidence / "upstream-file-hashes").mkdir(parents=True)
        (self.evidence / "upstream-staging-snapshot.yaml").write_text(
            f"snapshots:\n  ecc: {{repo: affaan-m/ECC, branch: main, head: {self.sha}}}\n", encoding="utf-8")
        rows = "".join(f"{git_blob_sha1(t.encode())}\t{len(t.encode())}\t{p}\n" for p, t in sorted(FILES.items()))
        (self.evidence / "upstream-file-hashes" / "ecc.tsv").write_text(f"# ecc @ {self.sha}\nblob_sha1\tbytes\tpath\n{rows}",
                                                                       encoding="utf-8")
        self.home = base / "home"
        self.env = mock.patch.dict(os.environ, {"AGYLITE_UPSTREAM_BASE": str(base / "remote")})
        self.env.start()
        self.cat = catalog.build(self.staging, self.evidence, {("ecc", "skills/golang-patterns/SKILL.md"): "ecc/golang-patterns"})

    def tearDown(self):
        self.env.stop()
        self.tmp.cleanup()


class TestCatalog(Fixture):
    def test_one_canonical_copy_per_name(self):
        ids = [e["id"] for e in self.cat["skills"]]
        self.assertEqual(sorted(ids), ["ecc/golang-patterns", "ecc/linear-sync", "ecc/swiftui-patterns"])
        swift = next(e for e in self.cat["skills"] if e["id"] == "ecc/swiftui-patterns")
        self.assertEqual(swift["path"], "skills/swiftui-patterns/SKILL.md")   # never docs/ja-JP/, .kiro/ or legacy/
        self.assertEqual(self.cat["skipped_copies"], 2)

    def test_swiftui_search_returns_the_canonical_skill(self):
        top = catalog.search(self.cat, "SwiftUI screen", 5)[0]
        self.assertEqual((top["id"], top["path"]), ("ecc/swiftui-patterns", "skills/swiftui-patterns/SKILL.md"))

    def test_bundled_skills_point_at_skill_load(self):
        text = catalog.render(catalog.search(self.cat, "Go error handling", 1))
        self.assertIn("bundled: `agylite skill load ecc/golang-patterns`", text)

    def test_policy_skill_is_listed_but_never_fetched(self):
        mcp = next(e for e in self.cat["skills"] if e["id"] == "ecc/linear-sync")
        self.assertEqual(mcp["policy"], ["MCP configuration"])
        self.assertIn("policy: MCP configuration (not fetchable)", catalog.render([mcp]))
        with self.assertRaises(PermissionError):
            catalog.get(self.home, self.cat, "ecc/linear-sync", {})

    def test_get_fetches_the_folder_at_its_pin_with_provenance(self):
        dest = catalog.get(self.home, self.cat, "ecc/swiftui-patterns", {"ecc": {"license": "MIT", "attribution": "x"}},
                           log=lambda *_: None)
        self.assertEqual((dest / "SKILL.md").read_text(encoding="utf-8"), SWIFT)
        self.assertTrue((dest / "references" / "state.md").is_file())
        prov = __import__("json").loads((dest / ".agylite-provenance.json").read_text(encoding="utf-8"))
        self.assertEqual((prov["commit"], prov["license"], prov["dangling_links"]), (self.sha, "MIT", []))


class TestRealCatalog(unittest.TestCase):
    def test_installed_bundle_swiftui(self):
        from agylite.paths import current_bundle
        bundle = current_bundle()
        if bundle is None or not (bundle / "catalog.json").is_file():
            self.skipTest("no installed bundle with a skill catalog")
        top = catalog.search(catalog.load(bundle), "SwiftUI", 5)[0]
        self.assertEqual(top["id"], "ecc/swiftui-patterns")
        self.assertFalse(catalog.is_copy(top["path"]))


if __name__ == "__main__":
    unittest.main()
