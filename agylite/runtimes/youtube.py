"""YouTube tools runtime (MP5 §2.3, youtube/*): `agylite youtube <tool> …` runs one of youtube-agent-skill's stdlib
scripts from the active bundle (`python3 -I <bundle>/files/ytagent/skills/<skill>/<tool>.py …`) in the project, with
the arguments passed through and the exit code preserved. Nothing renders, cuts or uploads video.

`voice init` copies the bundled template to `~/.agylite/youtube/voice.md` (host-neutral; upstream used
~/.claude/youtube/voice.md) only when the file is absent, so a filled voice file is never overwritten.
"""
import hashlib
import shutil
import subprocess
import sys
from pathlib import Path

TOOLS = {"hookscore": "yt-script/hookscore.py", "title": "yt-package/title.py", "deadair": "yt-edit/deadair.py",
         "chapters": "yt-chapters/chapters.py", "retention": "yt-retention/retention.py", "swipe": "yt-viral/swipe.py"}
ROOT = Path("files/ytagent")
TEMPLATE = ROOT / "templates" / "voice.md"
NEXT = "fill this in, or send me three of your videos and say 'write my voice.md from these'"


class YouTubeError(RuntimeError):
    pass


def tool_path(bundle_dir: Path | None, tool: str) -> Path:
    if tool not in TOOLS:
        raise YouTubeError(f"unknown youtube tool {tool!r}; use one of {', '.join(TOOLS)}")
    p = Path(bundle_dir) / ROOT / "skills" / TOOLS[tool] if bundle_dir else None
    if p is None or not p.is_file():
        raise YouTubeError("no active bundle with files/ytagent (run `agylite bundle build`)")
    return p


def command(bundle_dir, tool, args) -> list:
    return [sys.executable, "-I", str(tool_path(bundle_dir, tool)), *args]


def run(bundle_dir, tool, args, cwd: Path, capture=False) -> subprocess.CompletedProcess:
    return subprocess.run(command(bundle_dir, tool, args), cwd=cwd, capture_output=capture, text=True)


def voice_path(home: Path) -> Path:
    return Path(home) / "youtube" / "voice.md"


def voice_status(bundle_dir, home) -> str:
    """missing | template (still the unfilled template) | filled."""
    path = voice_path(home)
    if not path.is_file():
        return "missing"
    tpl = Path(bundle_dir) / TEMPLATE if bundle_dir else None
    same = tpl is not None and tpl.is_file() and (
        hashlib.sha256(path.read_bytes()).digest() == hashlib.sha256(tpl.read_bytes()).digest())
    return "template" if same else "filled"


def voice_init(bundle_dir, home) -> dict:
    """Copy the template when the voice file is absent; never overwrite (idempotent)."""
    path = voice_path(home)
    if path.is_file():
        return {"voice": str(path), "created": False, "status": voice_status(bundle_dir, home), "next": NEXT}
    tpl = Path(bundle_dir) / TEMPLATE if bundle_dir else None
    if tpl is None or not tpl.is_file():
        raise YouTubeError("no active bundle with the voice.md template (run `agylite bundle build`)")
    path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(tpl, path)
    return {"voice": str(path), "created": True, "status": "template", "next": NEXT}


def health(bundle_dir, home) -> dict:
    try:
        tool_path(bundle_dir, "hookscore")
    except YouTubeError as exc:
        return {"runtime": "youtube", "status": "no-bundle", "reason": str(exc)}
    return {"runtime": "youtube", "status": "ready", "tools": ", ".join(TOOLS),
            "voice": f"{voice_status(bundle_dir, home)} ({voice_path(home)})"}


def self_test(bundle_dir, fixtures: Path) -> dict:
    """Bundle self-test: hookscore and title score the fixture lines and exit 0."""
    codes = {"hookscore": run(bundle_dir, "hookscore", ["--hook", (fixtures / "hook.txt").read_text().strip()],
                              cwd=fixtures, capture=True).returncode,
             "title": run(bundle_dir, "title", ["--title", "I tested 7 AI agents for 30 days",
                                                "--thumb", "ONE WON"], cwd=fixtures, capture=True).returncode}
    return {"runtime": "youtube", "exit_codes": codes, "ok": not any(codes.values())}
