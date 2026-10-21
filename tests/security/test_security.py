import os
import re
import unittest
import yaml

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))

class TestSecurity(unittest.TestCase):
    def test_no_mcp_configs(self):
        mcp_file = os.path.join(ROOT_DIR, ".mcp.json")
        self.assertFalse(os.path.exists(mcp_file), ".mcp.json must not exist")
        
        for root, _, files in os.walk(ROOT_DIR):
            # .staging/ holds gitignored upstream audit snapshots, not plugin content (D-003)
            if ".git" in root or ".staging" in root:
                continue
            for file in files:
                if file.endswith((".json", ".yaml", ".yml")) and not file.endswith("CLAUDE.md"):
                    path = os.path.join(root, file)
                    with open(path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                        self.assertNotIn("mcpServers", content, f"mcpServers found in {path}")

    def test_no_vendor_directories(self):
        vendor_path = os.path.join(ROOT_DIR, "vendor")
        self.assertFalse(os.path.exists(vendor_path), "vendor directory must not exist")

    def test_repo_never_contains_a_built_bundle(self):
        # D-023: upstream files are fetched and built into $AGYLITE_HOME at install, never committed here.
        for name in ("bundles", "files", "blobs"):
            self.assertFalse(os.path.exists(os.path.join(ROOT_DIR, name)), f"{name}/ must not exist in the repo")
        third_party = os.path.join(ROOT_DIR, "third_party")
        if os.path.isdir(third_party):
            self.assertEqual(sorted(os.listdir(third_party)), ["licenses.json"],
                             "third_party/ holds only the generated license index; license texts live in the bundle")

    def test_all_dependencies_pinned_40_hex_sha(self):
        # Upstream pins live in the audited snapshot and flow into every provenance record and registry entry (P7).
        snap_path = os.path.join(ROOT_DIR, "docs", "audit", "evidence", "upstream-staging-snapshot.yaml")
        with open(snap_path, "r", encoding="utf-8") as f:
            snapshots = yaml.safe_load(f)["snapshots"]
        hex_sha_regex = re.compile(r'^[0-9a-f]{40}$')
        self.assertEqual(len(snapshots), 16)  # 14 + Appllama (D-034) + Pocock (MP3 §1.1)
        for name, meta in snapshots.items():
            self.assertTrue(hex_sha_regex.match(meta.get("head", "")),
                            f"Upstream {name} head '{meta.get('head')}' is not a valid 40-character hexadecimal SHA")

    def test_no_giant_prompt_files(self):
        for prohibited in ["SYSTEM.md", "MASTER_PROMPT.md"]:
            path = os.path.join(ROOT_DIR, prohibited)
            self.assertFalse(os.path.exists(path), f"Prohibited giant prompt file {prohibited} exists")

if __name__ == "__main__":
    unittest.main()
