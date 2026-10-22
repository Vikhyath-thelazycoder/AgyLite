"""MP5 §2.5: the YouTube tools run through `agylite youtube <tool>` (bundle scripts, args passed through, exit code
kept) and match golden outputs on the fixtures; `voice init` is idempotent and never overwrites a filled file; every
youtube-agent-skill rewrite still matches upstream (drift fails the build)."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.insert(0, ROOT_DIR)

from agylite.bundle.transforms import rewrites  # noqa: E402
from agylite.runtimes import youtube  # noqa: E402

UPSTREAM = Path.home() / "Developer" / "os" / "youtube-agent-skill"
FIXTURES = Path(ROOT_DIR) / "tests" / "fixtures" / "youtube"
GOLDEN = {  # tool, args, golden file
    "hookscore": (["hook.txt"], "hookscore.txt"),
    "title": (["--title", "I tested 7 AI agents for 30 days", "--thumb", "ONE WON", "--json"], "title.json"),
    "deadair": (["transcript.srt", "--json"], "deadair.json"),
    "chapters": (["transcript.srt", "--target", "4", "--json"], "chapters.json"),
    "retention": (["retention.csv", "--transcript", "transcript.srt", "--duration", "120", "--json"], "retention.json"),
    "swipe": (["collected.json", "--min", "2.0", "--json"], "swipe.json"),
}


def stable_chapters(text):
    data = json.loads(text)
    return {k: ([{kk: vv for kk, vv in c.items() if kk != "draft_title"} for c in v] if isinstance(v, list) else v)
            for k, v in data.items()}


def bundle_from_upstream(base: Path) -> Path:
    files = base / "bundle" / "files" / "ytagent"
    shutil.copytree(UPSTREAM / "skills", files / "skills")
    (files / "templates").mkdir(parents=True)
    text = (UPSTREAM / "templates" / "voice.md").read_text(encoding="utf-8")
    (files / "templates" / "voice.md").write_text(rewrites.apply("ytagent", "templates/voice.md", text), encoding="utf-8")
    return base / "bundle"


@unittest.skipUnless((UPSTREAM / "skills").is_dir(), "youtube-agent-skill upstream clone not present")
class TestYouTubeTools(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.bundle, self.home = bundle_from_upstream(self.base), self.base / "home"

    def tearDown(self):
        self.tmp.cleanup()

    def test_golden_outputs(self):
        for tool, (args, golden) in GOLDEN.items():
            with self.subTest(tool=tool):
                p = youtube.run(self.bundle, tool, args, cwd=FIXTURES, capture=True)
                self.assertEqual(p.returncode, 0, p.stderr)
                want = (FIXTURES / "golden" / golden).read_text(encoding="utf-8")
                if tool == "chapters":   # volatile: titles are topic words picked in set (hash) order; boundaries are stable
                    self.assertEqual(stable_chapters(p.stdout), stable_chapters(want))
                else:
                    self.assertEqual(p.stdout, want)

    def test_command_runs_bundle_script_isolated(self):
        argv = youtube.command(self.bundle, "hookscore", ["--hook", "x"])
        self.assertEqual(argv[:2], [sys.executable, "-I"])
        self.assertEqual(Path(argv[2]), self.bundle / "files/ytagent/skills/yt-script/hookscore.py")
        self.assertEqual(argv[3:], ["--hook", "x"])

    def test_exit_code_preserved(self):
        p = youtube.run(self.bundle, "deadair", ["missing.srt"], cwd=FIXTURES, capture=True)
        self.assertNotEqual(p.returncode, 0)

    def test_unknown_tool(self):
        with self.assertRaises(youtube.YouTubeError):
            youtube.command(self.bundle, "render", [])

    def test_voice_init_idempotent_never_overwrites(self):
        first = youtube.voice_init(self.bundle, self.home)
        self.assertTrue(first["created"])
        self.assertEqual(first["status"], "template")
        self.assertIn("three of your videos", first["next"])
        voice = youtube.voice_path(self.home)
        self.assertIn("~/.agylite/youtube/voice.md", voice.read_text(encoding="utf-8"))
        self.assertFalse(youtube.voice_init(self.bundle, self.home)["created"])
        voice.write_text("# voice.md\n\nI talk fast.\n", encoding="utf-8")
        again = youtube.voice_init(self.bundle, self.home)
        self.assertEqual((again["created"], again["status"]), (False, "filled"))
        self.assertEqual(voice.read_text(encoding="utf-8"), "# voice.md\n\nI talk fast.\n")

    def test_self_test(self):
        self.assertTrue(youtube.self_test(self.bundle, FIXTURES)["ok"])


@unittest.skipUnless((UPSTREAM / "skills").is_dir(), "youtube-agent-skill upstream clone not present")
class TestYouTubeRewrites(unittest.TestCase):
    def test_every_rewrite_matches_upstream(self):
        for (repo, path) in [k for k in rewrites.REWRITES if k[0] == "ytagent"]:
            with self.subTest(path=path):
                out = rewrites.apply(repo, path, (UPSTREAM / path).read_text(encoding="utf-8"))
                self.assertNotIn("~/.claude/youtube", out)
                self.assertNotIn("python3 ", out)
                self.assertNotRegex(out, r"`/yt-")

    def test_skills_name_agylite_commands(self):
        out = rewrites.apply("ytagent", "skills/yt-edit/SKILL.md",
                             (UPSTREAM / "skills/yt-edit/SKILL.md").read_text(encoding="utf-8"))
        self.assertIn("agylite youtube deadair", out)
        self.assertIn("agylite research video <url> --subs", out)
        self.assertNotIn("faster-whisper", out)   # "whisper json" stays: it is an input format the tool reads
        out = rewrites.apply("ytagent", "skills/yt-viral/SKILL.md",
                             (UPSTREAM / "skills/yt-viral/SKILL.md").read_text(encoding="utf-8"))
        self.assertIn("agylite research channel <channel-url>", out)
        out = rewrites.apply("ytagent", "skills/yt-script/SKILL.md",
                             (UPSTREAM / "skills/yt-script/SKILL.md").read_text(encoding="utf-8"))
        self.assertIn("generic voice", out)
        self.assertIn("Nothing here publishes", out)   # the gate stays verbatim


if __name__ == "__main__":
    unittest.main()
