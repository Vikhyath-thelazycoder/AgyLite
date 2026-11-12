"""Step 3 (owner 2026-11-04): no paid suite for BeyondSEO by default; its runtime is deterministic, so a free test runs
it, through Agylite's wrapper, on a local site with planted defects (crawl + offline audit; no network, no model).
Skipped when the SEO runtime is not installed (`agylite runtime install seo`)."""
import functools
import http.server
import json
import os
import sys
import tempfile
import threading
import unittest
from pathlib import Path

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.insert(0, ROOT_DIR)

from agylite.paths import agylite_home, current_bundle  # noqa: E402
from agylite.project.identity import detect  # noqa: E402
from agylite.runtimes import seo  # noqa: E402

SITE = Path(ROOT_DIR) / "tests" / "fixtures" / "seo" / "planted-site"
HOME, BUNDLE = agylite_home(), current_bundle()   # fixed at import: other test modules repoint AGYLITE_HOME
READY = seo.health(HOME, BUNDLE).get("status") == "ready"


@unittest.skipUnless(READY, "SEO runtime not installed")
class TestBeyondSEORuntime(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(SITE))
        handler.log_message = lambda *a: None
        cls.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.url = f"http://127.0.0.1:{cls.server.server_address[1]}/"
        cls.tmp = tempfile.TemporaryDirectory()
        out = Path(cls.tmp.name) / "crawl"
        proc, _ = seo.run(detect(Path(ROOT_DIR)), HOME, BUNDLE,
                          ["crawl", cls.url, "--allow-private", "--mode", "http", "--no-sitemaps", "--max-pages", "10",
                           "--quiet", "--no-color"], out=out, timeout=300)
        cls.crawl = (proc, out)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.tmp.cleanup()

    def issues(self):
        return {(i["code"], i["url"].rsplit("/", 1)[-1]) for i in json.loads((self.crawl[1] / "issues.json").read_text())}

    def test_crawl_finds_every_planted_defect_and_none_on_the_clean_page(self):
        self.assertEqual(self.crawl[0].returncode, 0, self.crawl[0].stderr[-800:])
        found = self.issues()
        for planted in [("missing_title", "about.html"), ("missing_description", "about.html"),
                        ("missing_image_alt", "about.html"), ("http_error", "menu.html"),
                        ("broken_internal_link", "")]:
            self.assertIn(planted, found)
        self.assertFalse({c for c, page in found if page == "" and c.startswith("missing_")}, found)

    def test_crawl_is_deterministic(self):
        out = Path(self.tmp.name) / "again"
        proc, _ = seo.run(detect(Path(ROOT_DIR)), HOME, BUNDLE,
                          ["crawl", self.url, "--allow-private", "--mode", "http", "--no-sitemaps", "--max-pages", "10",
                           "--quiet", "--no-color"], out=out, timeout=300)
        self.assertEqual(proc.returncode, 0)
        again = {(i["code"], i["url"].rsplit("/", 1)[-1]) for i in json.loads((out / "issues.json").read_text())}
        self.assertEqual(again, self.issues())

    def test_offline_audit_turns_the_crawl_into_findings(self):
        out = Path(self.tmp.name) / "audit"
        proc, _ = seo.run(detect(Path(ROOT_DIR)), HOME, BUNDLE,
                          ["audit", "--crawl", str(self.crawl[1]), "--offline", "--out", str(out)], timeout=300)
        self.assertEqual(proc.returncode, 0, proc.stderr[-800:])
        self.assertTrue((out / "audit.json").is_file())
        self.assertIn("about.html", (out / "audit.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
