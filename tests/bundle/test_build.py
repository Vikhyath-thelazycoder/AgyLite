import hashlib
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.insert(0, ROOT_DIR)

from agylite.bundle import build as bundle_build  # noqa: E402
from agylite.bundle.store import git_blob_sha1  # noqa: E402
from agylite.registry.generate import check, load_registry  # noqa: E402
from agylite.registry.loader import cards_hash  # noqa: E402

SHA = "a" * 40
FILES = {
    "LICENSE": "MIT License\n\nCopyright (c) 2026 Alpha Author\n",
    "skills/x/SKILL.md": "---\nname: x\ndescription: demo\n---\nUse [the reference](references/r.md).\n",
    "skills/x/references/r.md": "# Reference\nsame content\n",
    "docs/dup.md": "# Reference\nsame content\n",
    "docs/agent.mcp.json": '{"mcpServers": {"x": {"command": "npx"}}}\n',
    "notes/excluded.md": "not bundled\n",
}
RULES = """
version: 1
repos:
  alpha:
    default: {decision: EXCLUDE, reason: OUT_OF_DOMAIN}
    rules:
      - {paths: ["LICENSE"], decision: COPY, capability: engineering/planning, reason: LICENSE}
      - {paths: ["skills/**"], decision: ADAPT, capability: engineering/planning, reason: demo}
      - {paths: ["docs/dup.md"], decision: COPY, capability: engineering/planning, reason: demo}
"""


class Fixture:
    def __init__(self, tmp: Path, rules=RULES, files=FILES):
        self.staging, self.evidence, self.home = tmp / "staging", tmp / "evidence", tmp / "home"
        repo = self.staging / "alpha"
        for path, text in files.items():
            (repo / path).parent.mkdir(parents=True, exist_ok=True)
            (repo / path).write_text(text, encoding="utf-8")
        inv = self.evidence / "upstream-file-hashes"
        inv.mkdir(parents=True)
        rows = [f"{git_blob_sha1(text.encode())}\t{len(text.encode())}\t{path}" for path, text in sorted(files.items())]
        (inv / "alpha.tsv").write_text(f"# alpha @ {SHA}\nblob_sha1\tbytes\tpath\n" + "\n".join(rows) + "\n", encoding="utf-8")
        (self.evidence / "upstream-staging-snapshot.yaml").write_text(
            f"snapshots:\n  alpha: {{repo: demo/alpha, head: {SHA}}}\n", encoding="utf-8")
        self.rules = tmp / "rules.yaml"
        self.rules.write_text(rules, encoding="utf-8")
        self.licenses = tmp / "licenses.json"
        self.licenses.write_text(json.dumps({"alpha": {
            "license": "MIT", "attribution": "Copyright (c) 2026 Alpha Author", "license_files": ["LICENSE"],
            "note": None, "repository": "demo/alpha", "commit_sha": SHA, "bundled_files": 4}}), encoding="utf-8")

    def build(self, **kw):
        return bundle_build.build(self.home, self.staging, rules_path=self.rules, evidence=self.evidence,
                                  licenses_path=self.licenses, log=lambda *_: None, **kw)


class TestBuild(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_build_verify_activate(self):
        fx = Fixture(self.tmp)
        info = fx.build()
        self.assertEqual(info["status"], "known-good", info["errors"])
        self.assertEqual(info["counts"]["files"], 4)
        self.assertEqual(info["counts"]["unique_contents"], 3)
        bundle = fx.home / "bundles" / info["bundle_id"]
        self.assertEqual(os.readlink(fx.home / "bundles" / "current"), info["bundle_id"])
        self.assertEqual(bundle_build.verify(bundle), [])
        self.assertTrue((bundle / "third_party" / "alpha" / "LICENSE").is_file())
        self.assertFalse((bundle / "files" / "alpha" / "notes" / "excluded.md").exists())
        records = json.loads((bundle / "provenance.json").read_text())
        self.assertTrue(all(len(r["bundled_hash"]) == 64 for r in records))
        # single-link files (D-026): runtimes such as Unlazy reject hardlinked files
        self.assertEqual(os.stat(bundle / "files/alpha/docs/dup.md").st_nlink, 1)
        # P7: every bundle carries its generated registry
        reg = load_registry(bundle)
        self.assertEqual((reg["source"], reg["bundle_id"]), ("bundle", info["bundle_id"]))
        planning = reg["capabilities"]["engineering/planning"]
        self.assertEqual(planning["token_cost_estimate"]["bundled_files"], 4)
        self.assertEqual(planning["commit_sha"], {"demo/alpha": SHA})
        self.assertEqual(reg["capabilities"]["design/ux"]["source_repositories"], [])

    def test_rebuild_is_reproducible_and_reused(self):
        fx = Fixture(self.tmp)
        first = fx.build()
        second = fx.build()
        self.assertEqual(first["bundle_id"], second["bundle_id"])
        self.assertEqual(first["created"], second["created"])

    def test_reused_bundle_refreshes_stale_registry(self):
        fx = Fixture(self.tmp)
        info = fx.build()
        bundle = fx.home / "bundles" / info["bundle_id"]
        reg_file = bundle / "registry.yaml"
        reg_file.write_text(reg_file.read_text(encoding="utf-8").replace(cards_hash(), "stale"), encoding="utf-8")
        self.assertTrue(any("registry.yaml is stale" in p for p in check(bundle_dir=bundle)))
        fx.build()
        self.assertEqual(load_registry(bundle)["inputs_hash"], cards_hash())

    def test_tampered_bundle_detected(self):
        fx = Fixture(self.tmp)
        info = fx.build()
        bundle = fx.home / "bundles" / info["bundle_id"]
        (bundle / "files/alpha/skills/x/references/r.md").write_text("tampered\n", encoding="utf-8")
        self.assertTrue(any("hash mismatch" in p for p in bundle_build.verify(bundle)))

    def test_staging_drift_fails_build(self):
        fx = Fixture(self.tmp)
        (fx.staging / "alpha/docs/dup.md").write_text("changed after audit\n", encoding="utf-8")
        with self.assertRaises(bundle_build.BuildError):
            fx.build()

    def test_mcp_config_fails_build_and_never_activates(self):
        rules = RULES + '      - {paths: ["docs/agent.mcp.json"], decision: COPY, capability: engineering/planning, reason: demo}\n'
        fx = Fixture(self.tmp, rules=rules)
        info = fx.build()
        self.assertEqual(info["status"], "failed")
        self.assertTrue(any("MCP configuration" in e for e in info["errors"]))
        self.assertFalse((fx.home / "bundles" / "current").exists())

    def test_open_closure_gap_fails_build(self):
        rules = RULES.replace('["skills/**"]', '["skills/x/SKILL.md"]')
        fx = Fixture(self.tmp, rules=rules)
        info = fx.build()
        self.assertEqual(info["status"], "failed")
        self.assertTrue(any("open closure gap" in e for e in info["errors"]))

    def test_new_bundle_keeps_previous(self):
        fx = Fixture(self.tmp)
        first = fx.build()
        fx.rules.write_text(RULES + "# rules changed\n", encoding="utf-8")
        second = fx.build()
        self.assertNotEqual(first["bundle_id"], second["bundle_id"])
        bundles = fx.home / "bundles"
        self.assertEqual(os.readlink(bundles / "current"), second["bundle_id"])
        self.assertEqual(os.readlink(bundles / "previous"), first["bundle_id"])
        self.assertEqual([b["bundle_id"] for b in bundle_build.list_bundles(fx.home) if b["current"]], [second["bundle_id"]])



GEN_JS = """const cfg = require('./cfg');
exports.getPonytailInstructions = (level) => [
  'PONYTAIL MODE ACTIVE — level: ' + level, '',
  'Switch level: `/ponytail lite|full|ultra`. Off: "stop ponytail" or "normal mode".', '',
  'You are a lazy senior developer. ' + cfg.extra, 'token: ' + (process.env.AGY_SECRET_TOKEN || 'none'), ''].join('\\n');
"""
GEN_RULES = RULES + """      - {paths: ["hooks/gen.js"], decision: GENERATED, generator: ponytail-lite, inputs: ["hooks/cfg.js"], output: RULESET-lite.md, capability: engineering/simplicity, reason: "MP3 §2.1"}
"""


@unittest.skipUnless(shutil.which("node"), "node needed for the generated Ponytail ruleset")
class TestGeneratedRuleset(unittest.TestCase):
    """MP3 §2.1: the lite ruleset is generated from the upstream JS at build time, as untrusted input."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def fixture(self, js=GEN_JS, cfg="exports.extra = 'Least new code.';\n"):
        return Fixture(self.tmp, rules=GEN_RULES, files={**FILES, "hooks/gen.js": js, "hooks/cfg.js": cfg})

    def test_generates_the_ruleset_with_provenance(self):
        with mock.patch.dict(os.environ, {"AGY_SECRET_TOKEN": "s3cret"}):
            info = self.fixture().build()
        self.assertEqual(info["status"], "known-good", info["errors"])
        bundle = self.tmp / "home" / "bundles" / info["bundle_id"]
        text = (bundle / "files/alpha/RULESET-lite.md").read_text(encoding="utf-8")
        self.assertTrue(text.startswith(f"<!-- Generated by Agylite from demo/alpha@{SHA[:12]} hooks/gen.js, level lite"))
        self.assertIn("You are a lazy senior developer. Least new code.", text)
        self.assertIn("token: none", text)                                     # empty env: no tokens reach the JS
        self.assertNotIn("/ponytail lite|full|ultra", text)                     # Ponytail's own commands → Agylite
        self.assertIn("ponytail_ruleset: lite|off", text)
        rec = next(r for r in json.loads((bundle / "provenance.json").read_text()) if r["source_path"] == "hooks/gen.js")
        self.assertEqual((rec["integration_type"], rec["destination_path"]), ("GENERATED", "files/alpha/RULESET-lite.md"))
        self.assertEqual(rec["original_hash"], git_blob_sha1(GEN_JS.encode()))
        self.assertEqual(rec["bundled_hash"], hashlib.sha256(text.encode()).hexdigest())

    def test_untrusted_js_cannot_fail_open(self):
        cases = {
            "eval": "exports.getPonytailInstructions = () => eval('1 + 1') + '';\n",
            "too big": "exports.getPonytailInstructions = () => 'x'.repeat(9000);\n",
            "not text": "exports.getPonytailInstructions = () => 'a\\u0000b';\n",
            "throws": "exports.getPonytailInstructions = () => { throw new Error('boom'); };\n",
        }
        for name, js in cases.items():
            with self.subTest(name):
                with self.assertRaises(bundle_build.BuildError):
                    self.fixture(js=js).build()
                shutil.rmtree(self.tmp / "home", ignore_errors=True)
                shutil.rmtree(self.tmp / "staging", ignore_errors=True)
                shutil.rmtree(self.tmp / "evidence", ignore_errors=True)

    def test_timeout_and_missing_node_fail_the_build(self):
        from agylite.bundle.transforms import ponytail
        with mock.patch.object(ponytail, "TIMEOUT", 1):
            with self.assertRaises(bundle_build.BuildError):
                self.fixture(js="exports.getPonytailInstructions = () => { for (;;) {} };\n").build()
        shutil.rmtree(self.tmp / "staging"); shutil.rmtree(self.tmp / "evidence")   # noqa: E702
        with mock.patch("shutil.which", return_value=None):
            with self.assertRaisesRegex(bundle_build.BuildError, "Node.js"):
                self.fixture().build()

    def test_tampered_input_fails_the_build(self):
        fx = self.fixture()
        (fx.staging / "alpha" / "hooks" / "cfg.js").write_text("exports.extra = 'changed';\n", encoding="utf-8")
        with self.assertRaisesRegex(bundle_build.BuildError, "cfg.js"):
            fx.build()

    def test_fetch_includes_the_generator_inputs(self):
        from agylite.bundle.fetch import needed_paths
        from agylite.bundle.rules import evidence_dir
        paths = needed_paths(evidence_dir())["ponytail"]
        self.assertIn("hooks/ponytail-instructions.js", paths)
        self.assertIn("hooks/ponytail-config.js", paths)

if __name__ == "__main__":
    unittest.main()
