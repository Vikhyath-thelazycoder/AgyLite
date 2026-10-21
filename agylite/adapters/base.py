"""Host adapters (P19–P22, spec §33–34, D-042): thin packaging around ONE set of entry skills.

An adapter only renders host files (manifests, hooks, skill copies) and reports status. It contains no routing, state
or context logic: every host calls the same `agylite` CLI. Status levels are separate and never implied (§34):
FILES_PRESENT (packaging rendered and current) · INSTALLED (the host has it) · RUNTIME_VERIFIED (the host actually ran
`agylite bootstrap --host <name>`, recorded in $AGYLITE_HOME/hosts/<name>.json) · NOT_VERIFIED otherwise.
"""
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from .. import __version__
from ..paths import repo_root, agylite_home

HOSTS = ("claude-code", "codex", "cursor", "antigravity")
MANAGED = ".agylite-managed"
LEGACY = (".vikhyath-managed",)   # pre-rename installs (D-044)
DESCRIPTION = ("Agylite: one deterministic router, budgeted context, project state and local "
               "test-first verification over a curated bundle of engineering, codebase, design, testing, SEO and media "
               "capabilities. No MCP.")
POLICY_REF = "config/verification.yaml"


def _managed(d: Path) -> bool:
    return any((d / m).exists() for m in (MANAGED, *LEGACY))


def entry_skills(root: Path | None = None) -> dict:
    """skill name → SKILL.md text, from the one canonical set (skills/agylite-*)."""
    root = root or repo_root()
    return {p.parent.name: p.read_text(encoding="utf-8") for p in sorted((root / "skills").glob("agylite-*/SKILL.md"))}


def record_runtime(host: str, project_id: str | None, home: Path | None = None):
    """Called by `agylite bootstrap --host <host>`: the host really ran the OS (RUNTIME_VERIFIED evidence)."""
    if host not in HOSTS:
        return None
    path = (home or agylite_home()) / "hosts" / f"{host}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    data = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {"host": host, "first_seen": None}
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    data.update({"first_seen": data["first_seen"] or now, "last_seen": now, "os_version": __version__,
                 "bootstraps": data.get("bootstraps", 0) + 1, "last_project": project_id})
    path.write_text(json.dumps(data, indent=1) + "\n", encoding="utf-8")
    return data


def runtime_record(host: str, home: Path | None = None):
    path = (home or agylite_home()) / "hosts" / f"{host}.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None


class Adapter:
    host = ""
    # MP1 F15 (D-048): whether the host runs `agylite hook prompt` on every prompt. Hosts without a verified
    # prompt-submit hook carry the "route first" rule in their always-loaded text instead.
    prompt_hook = "unsupported"

    def __init__(self, root: Path | None = None, home: Path | None = None, user_home: Path | None = None):
        self.root = root or repo_root()
        self.home = home or agylite_home()
        self.user_home = user_home or Path.home()

    # ── packaging in the plugin repository ──────────────────────────────────────────────────────────────────────
    def repo_files(self) -> dict:
        """Repository-relative path → content this host needs in the plugin repo."""
        return {}

    def stale(self) -> list:
        return [rel for rel, text in self.repo_files().items()
                if not (self.root / rel).is_file() or (self.root / rel).read_text(encoding="utf-8") != text]

    def write_repo_files(self) -> list:
        changed = self.stale()
        for rel in changed:
            (self.root / rel).parent.mkdir(parents=True, exist_ok=True)
            (self.root / rel).write_text(self.repo_files()[rel], encoding="utf-8")
        return changed

    # ── user-level install (hosts without a plugin installer we drive) ─────────────────────────────────────────
    def skills_target(self) -> Path | None:
        return None

    def install(self) -> list:
        target = self.skills_target()
        if target is None:
            raise NotImplementedError(f"{self.host} installs through its own plugin manager; see `agylite adapters status`")
        written = []
        for name, text in entry_skills(self.root).items():
            d = target / name
            if d.exists() and not _managed(d):
                raise FileExistsError(f"{d} exists and is not managed by Agylite; not overwriting")
            d.mkdir(parents=True, exist_ok=True)
            (d / "SKILL.md").write_text(text, encoding="utf-8")
            (d / MANAGED).write_text(f"agylite {__version__}\n", encoding="utf-8")
            written.append(str(d))
        return written

    def uninstall(self) -> list:
        target = self.skills_target()
        removed = []
        if target is None or not target.is_dir():
            return removed
        for d in sorted([*target.glob("agylite-*"), *target.glob("vikhyath-*")]):
            if _managed(d):
                shutil.rmtree(d)
                removed.append(str(d))
        return removed

    def installed(self) -> dict:
        target = self.skills_target()
        if target is None:
            return {"installed": False, "how": "host plugin manager"}
        names = sorted(d.name for d in target.glob("agylite-*") if _managed(d)) if target.is_dir() else []
        return {"installed": bool(names), "where": str(target), "skills": names}

    def status(self) -> dict:
        stale = self.stale()
        inst = self.installed()
        run = runtime_record(self.host, self.home)
        level = ("RUNTIME_VERIFIED" if run and inst["installed"] else "INSTALLED" if inst["installed"] else
                 "FILES_PRESENT" if not stale else "NOT_VERIFIED")
        return {"host": self.host, "status": level, "files_current": not stale, "stale": stale,
                "prompt_hook": self.prompt_hook, **inst,
                "runtime": run, "policy": POLICY_REF}
