"""MP5 §1.6 (offline; subprocess and HTTP mocked): the research wrapper calls only its allow-listed tools, never Agent-Reach's
excluded modules; it has no write path on X or Reddit; credentials round-trip at mode 0600 and never appear in output,
logs or events; private URLs never go to Jina Reader; doctor reports the allowed channels only."""
import contextlib
import io
import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.insert(0, ROOT_DIR)

from agylite.research import secrets, web  # noqa: E402
from agylite.runtimes import research as rr  # noqa: E402

EXCLUDED = ("exa", "mcporter", "opencli", "cookie_extract", "transcribe", "browser_cookie", "agent-reach", "agent_reach")
WRITES = ("post", "tweet", "like", "unlike", "retweet", "reply", "follow", "bookmark", "delete", "comment", "vote",
          "upvote", "downvote", "save", "subscribe", "dm", "message")
SENTINEL = "SENTINEL0cookie0value0do0not0leak"


def every_argv():
    y, g, t, r = Path("/v/bin/yt-dlp"), Path("/usr/bin/gh"), Path("/v/bin/twitter"), Path("/v/bin/rdt")
    return [
        rr.video_argv(y, "https://youtu.be/x", "/tmp/o", subs=True), rr.video_argv(y, "https://youtu.be/x", "/tmp/o", meta=True),
        rr.video_argv(y, "https://youtu.be/x", "/tmp/o", comments=20), rr.video_search_argv(y, "q", 5),
        rr.channel_argv(y, "https://www.youtube.com/@chan", 30),
        *[rr.github_argv(g, "q", k) for k in rr.GH_TYPES],
        rr.x_argv(t, "q", 50), rr.reddit_argv(r, "q", sub="python", n=99), rr.reddit_argv(r, read="1abc"),
    ]


class TestAllowList(unittest.TestCase):
    def test_no_excluded_backend_in_any_argv(self):
        for argv in every_argv():
            joined = " ".join(map(str, argv)).lower()
            for bad in EXCLUDED:
                self.assertNotIn(bad, joined, argv)

    def test_read_only(self):
        for argv in every_argv():
            name = Path(argv[0]).name
            if name == "twitter":
                self.assertEqual(argv[1], "search")
            if name == "rdt":
                self.assertIn(argv[1], ("search", "read"))
            if name == "gh":
                self.assertEqual(argv[1], "search")
            self.assertFalse(set(map(str, argv[1:2])) & set(WRITES), argv)

    def test_limits(self):
        self.assertIn("20", rr.x_argv("twitter", "q", 50))
        self.assertIn("25", rr.reddit_argv("rdt", "q", n=99))

    def test_ytdlp_never_reads_browser_cookies_or_downloads(self):
        for argv in every_argv():
            if Path(argv[0]).name == "yt-dlp":
                for flag in ("--no-cookies-from-browser", "--no-cookies", "--ignore-config", "--skip-download"):
                    self.assertIn(flag, argv)
                self.assertNotIn("--cookies-from-browser", argv)

    def test_importing_the_wrapper_imports_no_excluded_module(self):
        code = ("import sys; import agylite.runtimes.research, agylite.research.web, agylite.research.secrets; "
                "bad=[m for m in sys.modules if m.split('.')[0] in ('agent_reach','browser_cookie3','mcp','playwright')]; "
                "print(bad)")
        p = subprocess.run([sys.executable, "-c", code], cwd=ROOT_DIR, capture_output=True, text=True,
                           env={**os.environ, "PYTHONPATH": ROOT_DIR})
        self.assertEqual(p.stdout.strip(), "[]", p.stderr)

    def test_extras_never_install_browser_cookie3(self):
        for spec in rr.EXTRAS.values():
            self.assertFalse(any("cookie" in d.lower() for d in spec["deps"]))
        self.assertIn("browser-cookie3", rr.FORBIDDEN_PACKAGES)


class TestChildEnv(unittest.TestCase):
    def test_private_home_minimal_path_no_inherited_secrets(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(os.environ, {
                "OPENAI_API_KEY": "sk", "TWITTER_AUTH_TOKEN": "inherited", "PATH": "/Users/me/.local/bin:/opt/uv/bin"}):
            env = rr.child_env(Path(tmp), None if False else Path(tmp), Path(tmp) / "h", extra={"TWITTER_CT0": "c"})
        self.assertEqual(env["HOME"], str(Path(tmp) / "h"))
        self.assertNotIn("OPENAI_API_KEY", env)
        self.assertNotIn("TWITTER_AUTH_TOKEN", env)
        self.assertEqual(env["TWITTER_CT0"], "c")
        self.assertNotIn(".local/bin", env["PATH"])
        self.assertNotIn("uv", env["PATH"])

    def test_credentials_reach_only_the_one_child(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            seen = {}

            def fake_run(argv, **kw):
                seen.update(argv=argv, env=kw["env"], cwd=kw["cwd"],
                            cred=(Path(kw["cwd"]) / ".config/rdt-cli/credential.json").read_text())
                seen["mode"] = stat.S_IMODE((Path(kw["cwd"]) / ".config/rdt-cli/credential.json").stat().st_mode)
                return subprocess.CompletedProcess(argv, 0, "[]", "")
            with mock.patch.object(secrets, "load", return_value={"reddit_session": SENTINEL}), \
                    mock.patch.object(rr, "info", return_value={"extras": ["reddit"]}), \
                    mock.patch.object(rr, "runtime_dir", return_value=home / "rt"), \
                    mock.patch("subprocess.run", fake_run):
                rr.reddit(home, None, "bun 2", n=5)
            self.assertIn(SENTINEL, seen["cred"])
            self.assertEqual(seen["mode"], 0o600)
            self.assertNotIn(SENTINEL, " ".join(map(str, seen["argv"])))
            self.assertNotIn(SENTINEL, json.dumps(seen["env"]))
            self.assertFalse(Path(seen["cwd"]).exists())           # the private HOME is deleted afterwards
            self.assertTrue(str(seen["cwd"]).startswith(str(home / "secrets")))

    def test_disabled_channels_refuse(self):
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(rr, "info", return_value={"extras": []}):
                with self.assertRaisesRegex(rr.ResearchError, "agylite research enable x"):
                    rr.x(Path(tmp), None, "q")
                with self.assertRaisesRegex(rr.ResearchError, "enable reddit"):
                    rr.reddit(Path(tmp), None, "q")


class TestSecrets(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name) / ".agylite"
        self.env = mock.patch.dict(os.environ, {"AGYLITE_SECRETS_BACKEND": "file"})
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.tmp.cleanup()

    def test_round_trip_modes_and_delete(self):
        self.assertEqual(secrets.store(self.home, "x", {"auth_token": SENTINEL, "ct0": SENTINEL + "2"}), "file")
        f = secrets.secrets_dir(self.home) / "research.env"
        self.assertEqual(stat.S_IMODE(f.stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(f.parent.stat().st_mode), 0o700)
        self.assertEqual(secrets.load(self.home, "x"), {"auth_token": SENTINEL, "ct0": SENTINEL + "2"})
        self.assertNotIn(SENTINEL, (f.parent / "research.json").read_text())   # metadata holds names only
        self.assertEqual(secrets.status(self.home, "x"), "enabled (file)")
        self.assertTrue(secrets.delete(self.home, "x"))
        self.assertEqual(secrets.load(self.home, "x"), {})
        self.assertNotIn(SENTINEL, f.read_text())
        self.assertEqual(secrets.status(self.home, "x"), "disabled")

    def test_bad_values_are_rejected_without_echo(self):
        with self.assertRaises(secrets.SecretError) as ctx:
            secrets.store(self.home, "reddit", {"reddit_session": "has space " + SENTINEL})
        self.assertNotIn(SENTINEL, str(ctx.exception))

    def test_keychain_values_go_over_stdin_not_argv(self):
        calls = []
        with mock.patch.dict(os.environ, {"AGYLITE_SECRETS_BACKEND": "keychain"}), \
                mock.patch("subprocess.run", lambda argv, **kw: calls.append((argv, kw.get("input"))) or
                           subprocess.CompletedProcess(argv, 0, "", "")):
            secrets.store(self.home, "reddit", {"reddit_session": SENTINEL})
        argv, stdin = calls[0]
        self.assertEqual(argv, ["security", "-i"])
        self.assertIn(SENTINEL, stdin)
        self.assertNotIn(SENTINEL, " ".join(argv))

    def test_cli_enable_never_prints_or_logs_the_value(self):
        from agylite import cli
        out, err = io.StringIO(), io.StringIO()
        with mock.patch.dict(os.environ, {"AGYLITE_HOME": str(self.home)}), \
                mock.patch("getpass.getpass", return_value=SENTINEL), \
                mock.patch.object(rr, "add_extra", return_value={"extras": ["reddit"]}), \
                contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = cli.main(["research", "enable", "reddit"])
        self.assertEqual(code, 0)
        self.assertNotIn(SENTINEL, out.getvalue() + err.getvalue())
        for p in self.home.rglob("*"):
            if p.is_file() and p.name != "research.env":
                self.assertNotIn(SENTINEL, p.read_text(errors="ignore"), p)


class TestJinaGuard(unittest.TestCase):
    def test_private_urls_refused(self):
        for url in ("http://localhost:3000/admin", "http://127.0.0.1/x", "http://10.0.0.4/", "http://192.168.1.2/",
                    "http://172.20.1.1/", "http://[::1]/", "https://printer.local/", "https://wiki.corp.internal/a",
                    "https://api.example.com/x?api_key=abc", "https://x.com/a?token=1", "https://cdn.example.com/f?sig=z",
                    "http://intranet/", "ftp://example.com/f"):
            with self.subTest(url=url):
                self.assertIsNotNone(web.private_reason(url))
                with self.assertRaises(web.ReadError):
                    web.jina_url(url)

    def test_public_urls_allowed(self):
        self.assertEqual(web.jina_url("https://docs.python.org/3/"), "https://r.jina.ai/https://docs.python.org/3/")
        self.assertIsNone(web.private_reason("https://github.com/a/b?tab=readme"))

    def test_read_uses_jina_and_direct(self):
        calls = []

        def fake_get(url, headers=None):
            calls.append(url)
            return ("Title: T\n\nbody" if "jina" in url else
                    "<html><title>Doc</title><nav>menu</nav><main><h1>Hello</h1><p>World of text.</p></main></html>",
                    "text/html" if "jina" not in url else "text/plain")
        with mock.patch.object(web, "_get", fake_get):
            self.assertEqual(web.read("https://example.org/a")["via"], "r.jina.ai")
            page = web.read("http://localhost:8000/", direct=True)
        self.assertEqual(calls, ["https://r.jina.ai/https://example.org/a", "http://localhost:8000/"])
        self.assertEqual(page["title"], "Doc")
        self.assertIn("# Hello", page["text"])
        self.assertNotIn("menu", page["text"])


class TestHelpers(unittest.TestCase):
    def test_auto_subtitles_deduplicated(self):
        vtt = ("WEBVTT\nKind: captions\nLanguage: en\n\n00:00:01.000 --> 00:00:03.000\nhello there\n\n"
               "00:00:03.000 --> 00:00:05.000\nhello there\n<00:00:03.500><c>general</c> kenobi\n\n"
               "00:00:05.000 --> 00:00:07.000\n<c>general</c> kenobi\n")
        self.assertEqual(web.vtt_lines(vtt), [(1.0, "hello there"), (3.0, "general kenobi")])

    def test_swipe_rows(self):
        listing = {"channel": "Desk Lab", "entries": [{"id": "a1", "title": "T", "view_count": 10, "duration": 61},
                                                      {"id": "b2", "title": "no views"}]}
        self.assertEqual(web.swipe_rows(listing, "u"), [{"channel": "Desk Lab", "title": "T", "views": 10,
                                                          "url": "https://www.youtube.com/watch?v=a1", "duration": 61}])

    def test_channel_root_gets_videos_tab(self):
        self.assertTrue(rr.channel_argv("yt-dlp", "https://www.youtube.com/@chan", 5)[-1].endswith("/@chan/videos"))


class TestDoctor(unittest.TestCase):
    def test_nothing_enabled(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(rr, "info", return_value={"yt_dlp": "2026.07.04",
                                                                                                "extras": []}), \
                mock.patch.object(rr, "cookie_reader_absent", return_value=True), \
                mock.patch("shutil.which", return_value=None):
            rows = rr.doctor(Path(tmp), None)
        self.assertTrue(rows["web"].startswith("ok"))
        self.assertTrue(rows["rss"].startswith("ok"))
        self.assertTrue(rows["video"].startswith("ok"))
        self.assertEqual(rows["x"], "disabled")
        self.assertEqual(rows["reddit"], "disabled (rdt-cli unmaintained upstream since 2026-03)")
        self.assertEqual(rows["github"], "missing gh (GitHub CLI)")
        self.assertIn("never read", rows["browser cookies"])
        self.assertEqual(set(rows), {"web", "rss", "video", "github", "x", "reddit", "browser cookies"})


if __name__ == "__main__":
    unittest.main()
