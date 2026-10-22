"""MP4 §2.3–2.4: `agylite design extract` — 1-3 inspiration URLs → designlang per site (+ pair) → one DESIGN.md with
its sources, `mode: inspiration` and any design-check overrides; systems, never identity. A fake runtime writes canned
designlang output (tests/fixtures/designlang/), so nothing here needs node, a browser or the network."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.insert(0, ROOT_DIR)

from agylite.design import extract  # noqa: E402

FIX = Path(ROOT_DIR) / "tests" / "fixtures" / "designlang"
SITE_MD = (FIX / "site-DESIGN.md").read_text(encoding="utf-8")


class FakeRuntime:
    bin, node, pkg, version = "designlang", "node", Path("/pkg/designlang"), "13.3.2"

    def env(self):
        return {"PLAYWRIGHT_BROWSERS_PATH": "/rt/browsers"}


class Recorder:
    """Runs nothing: records argv/env and writes what designlang would."""

    def __init__(self):
        self.calls = []

    def __call__(self, argv, env, cwd):
        self.calls.append((argv, env))
        out = Path(argv[argv.index("--out") + 1])
        (out if argv[0] == "designlang" else out.parent).mkdir(parents=True, exist_ok=True)
        if argv[0] == "designlang" and argv[1] == "pair":
            (out / "a-x-b.pair.md").write_text("# pair\n", encoding="utf-8")
            (out / "a-x-b.pair.json").write_text("{}", encoding="utf-8")
        elif argv[0] == "designlang":
            host = extract.host_of(argv[1])
            (out / f"{host}-DESIGN.md").write_text(SITE_MD.replace("https://harbour.example", argv[1]), encoding="utf-8")
            shutil.copy(FIX / "site-design-tokens.json", out / f"{host}-design-tokens.json")
        else:   # the fuse script writes one merged DESIGN.md
            Path(argv[argv.index("--out") + 1]).write_text(SITE_MD, encoding="utf-8")
        return 0


UPSTREAM_FORMATTER = Path.home() / "Developer" / "os" / "design-extract" / "src" / "formatters" / "design-md.js"


class TestDesignMdSections(unittest.TestCase):
    @unittest.skipUnless(UPSTREAM_FORMATTER.is_file(), "design-extract clone not present")
    def test_sections_match_designlangs_formatter(self):
        """MP4 §4: the 8 canonical sections are designlang's own (formatDesignMd), the generator Agylite follows."""
        import re
        src = UPSTREAM_FORMATTER.read_text(encoding="utf-8")
        found = [m[1] for m in re.findall(r"\[\s*(['\"])(.+?)\1,\s+section\w+\(design\)\]", src)]
        self.assertEqual(tuple(found), extract.DESIGN_MD_SECTIONS)


class TestValidation(unittest.TestCase):
    def test_urls_are_checked(self):
        self.assertEqual(extract.validate_urls(["https://linear.app", "vercel.com"]),
                         ["https://linear.app", "https://vercel.com"])
        for bad in (["file:///etc/passwd"], ["http://localhost:3000"], ["http://127.0.0.1"], ["http://10.1.2.3/x"],
                    ["http://192.168.1.4"], ["http://[::1]/"], ["http://printer.local"], ["ftp://x.org"],
                    ["https://a.com", "https://b.com", "https://c.com", "https://d.com"], []):
            with self.subTest(bad), self.assertRaises(extract.ExtractError):
                extract.validate_urls(bad)
        self.assertEqual(extract.validate_urls(["http://localhost:3000"], allow_local=True), ["http://localhost:3000"])

    def test_api_keys_never_reach_designlang(self):
        env = extract.child_env({"OPENAI_API_KEY": "x", "ANTHROPIC_API_KEY": "y", "ATLASCLOUD_KEY": "z",
                                 "ATLAS_CLOUD_TOKEN": "w", "GITHUB_TOKEN": "v", "PATH": "/bin"}, FakeRuntime().env())
        self.assertEqual(set(env), {"PATH", "PLAYWRIGHT_BROWSERS_PATH"})


class TestExtract(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def run_extract(self, urls, **kw):
        rec = Recorder()
        result = extract.run(self.root, urls, runtime=FakeRuntime(), runner=rec, **kw)
        return rec, result

    def front(self, path):
        return yaml.safe_load(path.read_text(encoding="utf-8").split("---", 2)[1])

    def test_one_url_one_designlang_run_and_a_design_md(self):
        rec, r = self.run_extract(["https://linear.app"], dark=True, depth=2)
        self.assertEqual([c[0][:2] for c in rec.calls], [["designlang", "https://linear.app"]])
        argv = rec.calls[0][0]
        self.assertIn("--dark", argv)
        self.assertEqual(argv[argv.index("--depth") + 1], "2")
        self.assertNotIn("--smart", argv)
        self.assertEqual(r["design_md"], str(self.root / "DESIGN.md"))
        fm = self.front(self.root / "DESIGN.md")
        self.assertEqual(fm["mode"], "inspiration")
        self.assertEqual([s["url"] for s in fm["sources"]], ["https://linear.app"])
        self.assertEqual(fm["sources"][0]["designlang"], "13.3.2")
        text = (self.root / "DESIGN.md").read_text(encoding="utf-8")
        for h in extract.DESIGN_MD_SECTIONS:
            self.assertIn(f"\n# {h}\n", text)

    def test_two_urls_add_pair_and_a_fused_design_md(self):
        rec, r = self.run_extract(["https://a.com", "https://b.com"], axes={"colors_from": "b", "typography_from": "a"})
        kinds = [extract.step_kind(c[0]) for c in rec.calls]
        self.assertEqual(kinds, ["site", "site", "pair", "fuse"])
        pair = rec.calls[2][0]
        self.assertEqual(pair[1:4], ["pair", "https://a.com", "https://b.com"])
        self.assertEqual(pair[pair.index("--colors-from") + 1], "b")
        self.assertEqual(pair[pair.index("--format") + 1], "all")
        fuse = rec.calls[3][0]
        self.assertEqual(fuse[fuse.index("--colors-from") + 1], "b")
        notes = (self.root / ".agylite/design/inspiration/MERGE_NOTES.md").read_text(encoding="utf-8")
        self.assertNotIn("## Third site", notes)

    def test_three_urls_pair_primary_with_second_and_write_merge_notes(self):
        rec, r = self.run_extract(["https://a.com", "https://b.com", "https://c.com"], primary="https://b.com")
        pair = next(c[0] for c in rec.calls if extract.step_kind(c[0]) == "pair")
        self.assertEqual(pair[2:4], ["https://b.com", "https://a.com"])
        notes = (self.root / ".agylite/design/inspiration/MERGE_NOTES.md").read_text(encoding="utf-8")
        self.assertIn("c.com", notes)
        for row in ("palette", "type", "spacing", "radii", "motion"):
            self.assertIn(f"| {row} |", notes)

    def test_identity_is_not_copied(self):
        """§2.4: the primary (brand) colour is shifted ≥ 20° in hue, and the change is written down."""
        self.run_extract(["https://linear.app"])
        fm = self.front(self.root / "DESIGN.md")
        new = fm["tokens"]["colors"]["primary"]
        self.assertNotEqual(new.lower(), "#0b5fff")
        self.assertGreaterEqual(extract.hue_distance("#0b5fff", new), 20)
        self.assertNotIn("#0b5fff", (self.root / "DESIGN.md").read_text(encoding="utf-8").lower())
        notes = (self.root / ".agylite/design/inspiration/MERGE_NOTES.md").read_text(encoding="utf-8")
        self.assertIn("#0b5fff", notes.lower())

    def test_existing_design_md_is_never_overwritten_without_replace(self):
        (self.root / "DESIGN.md").write_text("# Ours\n", encoding="utf-8")
        _, r = self.run_extract(["https://linear.app"])
        self.assertEqual((self.root / "DESIGN.md").read_text(encoding="utf-8"), "# Ours\n")
        self.assertEqual(r["design_md"], str(self.root / "docs/design/DESIGN.inspiration.md"))
        self.assertTrue(r["needs_replace_decision"])
        _, r = self.run_extract(["https://linear.app"], replace=True)
        self.assertEqual(r["design_md"], str(self.root / "DESIGN.md"))

    def test_overrides_written_when_the_system_needs_more_than_the_limits(self):
        _, r = self.run_extract(["https://linear.app"])
        fm = self.front(self.root / "DESIGN.md")
        self.assertEqual(fm["design_check_overrides"], {"radius_values": 5})     # 5 radii vs limit 4
        self.assertEqual(r["summary"]["radii"], [4, 8, 12, 16, 999])
        self.assertIn("#", r["summary"]["palette"][0])


class TestFuseScript(unittest.TestCase):
    """The fuse script fixes designlang 13.3.2's DESIGN.md input: breakpoint objects and duplicate radius labels."""

    @unittest.skipUnless(shutil.which("node"), "node not on PATH")
    def test_breakpoints_are_numbers_and_radius_labels_unique(self):
        with tempfile.TemporaryDirectory() as tmp:
            pkg = Path(tmp) / "designlang"
            (pkg / "src" / "formatters").mkdir(parents=True)
            (pkg / "src" / "index.js").write_text(
                "export async function extractDesignLanguage(url) { return { url,"
                " breakpoints: [{ value: 768, label: 'md', type: 'min-width' }, { value: 1024, label: 'lg' }],"
                " borders: { radii: [{ value: 6, label: 'md' }, { value: 9, label: 'md' }, { value: 16, label: 'lg' }] } }; }\n",
                encoding="utf-8")
            (pkg / "src" / "fuse.js").write_text("export function fuseDesigns(a, b) { return { design: a }; }\n",
                                                 encoding="utf-8")
            (pkg / "src" / "formatters" / "design-md.js").write_text(
                "export function formatDesignMd(d) { return JSON.stringify(d); }\n", encoding="utf-8")
            out = Path(tmp) / "out.json"
            script = Path(ROOT_DIR) / "agylite" / "design" / "fuse_design_md.mjs"
            subprocess.run(["node", str(script), "--pkg", str(pkg), "--a", "https://a.example", "--b",
                            "https://b.example", "--out", str(out)], check=True, capture_output=True)
            design = json.loads(out.read_text(encoding="utf-8"))
        self.assertEqual(design["breakpoints"], [768, 1024])
        self.assertEqual([r["label"] for r in design["borders"]["radii"]], ["md", "r9", "lg"])


if __name__ == "__main__":
    unittest.main()
