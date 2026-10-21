"""Skill catalog (IMPLEMENTATION_PLAN §2.1, Plan A's breadth without its cost).

At bundle build every SKILL.md of every pinned upstream is indexed into `<bundle>/catalog.json` (name, description,
repository, path, pin, size). Translations and host-port copies are skipped and one canonical copy is kept per
(upstream, name), preferring the upstream's main `skills/` path. Skills that carry MCP configuration, always-on hooks or
telemetry are listed with a `policy` note and can't be fetched. `agylite skills search` ranks the catalog (BM25 over
name + description); `agylite skills get <id>` fetches one skill folder at its pin into ~/.agylite/cache/skills/.
The catalog is never listed in every message; the L0 bootstrap names the command in one line.
"""
import json
import re
import shutil
import subprocess
from pathlib import Path

from .bundle.store import git_blob_sha1
from .context.sections import est_tokens, frontmatter
from .routing.fallback_bm25 import BM25

CATALOG = "catalog.json"
# Copies, not canonical skills: translations and per-host ports (Plan A picked a Japanese translation for "SwiftUI").
COPY_PATTERNS = [re.compile(p) for p in (
    r"(^|/)docs/[a-z]{2}(-[A-Za-z]{2,4})?/", r"(^|/)i18n/", r"(^|/)\.agents/", r"(^|/)\.kiro/", r"(^|/)\.cursor/",
    r"(^|/)\.codex/", r"(^|/)\.gemini/", r"(^|/)\.opencode/", r"(^|/)pi/", r"(^|/)\.windsurf/", r"(^|/)\.qoder/",
    r"(^|/)\.clinerules/", r"(^|/)\.openclaw/", r"(^|/)\.grok-plugin/", r"(^|/)\.kimi-plugin/", r"(^|/)\.devin-plugin/")]
POLICY_FILES = {".mcp.json": "MCP configuration", "mcp.json": "MCP configuration", "hooks.json": "always-on hooks"}
TELEMETRY = re.compile(r"\btelemetry\b", re.I)


def is_copy(path: str) -> bool:
    return any(p.search(path) for p in COPY_PATTERNS)


def _rank_path(path: str):
    """Canonical-copy preference: the upstream's main skills/ tree, then the shortest path."""
    return (not (path.startswith("skills/") or "/skills/" in path), path.count("/"), path)


def build(staging: Path, evidence: Path, bundled_sources: dict | None = None) -> dict:
    """Index every SKILL.md of every pinned upstream (verified against the audited blob hash)."""
    from .bundle.rules import load_yaml, read_inventory
    pins = load_yaml(evidence / "upstream-staging-snapshot.yaml")["snapshots"]
    bundled_sources = bundled_sources or {}
    entries, skipped_copies, missing = {}, 0, []
    for repo, meta in sorted(pins.items()):
        inv = read_inventory(evidence, repo)
        files_by_dir = {}
        for p, _n, _h in inv:
            files_by_dir.setdefault(p.rsplit("/", 1)[0] if "/" in p else "", []).append(p.rsplit("/", 1)[-1])
        for path, size, blob in inv:
            if path.rsplit("/", 1)[-1] != "SKILL.md":
                continue
            if is_copy(path):
                skipped_copies += 1
                continue
            src = staging / repo / path
            if not src.is_file():
                missing.append(f"{repo}:{path}")
                continue
            data = src.read_bytes()
            if git_blob_sha1(data) != blob:
                missing.append(f"{repo}:{path} (hash mismatch)")
                continue
            text = data.decode("utf-8", "replace")
            fm, _ = frontmatter(text)
            folder = path.rsplit("/", 1)[0] if "/" in path else ""
            name = str(fm.get("name") or folder.rsplit("/", 1)[-1] or repo).strip()
            policy = [why for f, why in POLICY_FILES.items() if f in files_by_dir.get(folder, [])]
            if re.search(r"^hooks\s*:", text[:4000], re.M):
                policy.append("always-on hooks (frontmatter)")
            if TELEMETRY.search(text):
                policy.append("telemetry")
            entry = {"id": f"{repo}/{name}", "repo": repo, "repository": meta["repo"], "name": name,
                     "description": " ".join(str(fm.get("description") or "").split())[:400], "path": path,
                     "pin": meta["head"], "bytes": size, "tokens": est_tokens(size),
                     "policy": sorted(set(policy)), "bundled": bundled_sources.get((repo, path))}
            key = (repo, name)
            if key not in entries or _rank_path(path) < _rank_path(entries[key]["path"]):
                entries[key] = entry
    items = sorted(entries.values(), key=lambda e: e["id"])
    return {"version": 1, "skills": items, "count": len(items), "skipped_copies": skipped_copies, "missing": missing}


def load(bundle: Path) -> dict:
    path = bundle / CATALOG
    if not path.is_file():
        raise FileNotFoundError("this bundle has no skill catalog (rebuild it: `agylite bundle build`)")
    return json.loads(path.read_text(encoding="utf-8"))


def search(catalog: dict, words: str, n: int = 5) -> list:
    skills = {e["id"]: e for e in catalog["skills"]}
    index = BM25({sid: f"{e['name']} {e['name'].replace('-', ' ')} {e['description']}" for sid, e in skills.items()})
    return [{**skills[sid], "score": round(score, 2)} for sid, score in index.score(words)[:n]]


def render(results) -> str:
    lines = []
    for e in results:
        how = (f"bundled: `agylite skill load {e['bundled']}`" if e.get("bundled") else
               f"policy: {', '.join(e['policy'])} (not fetchable)" if e["policy"] else f"`agylite skills get {e['id']}`")
        lines.append(f"{e['id']}  ({e['repository']}:{e['path']}, ~{e['tokens']} tokens)\n    {e['description'][:200]}\n"
                     f"    → {how}")
    return "\n".join(lines) + ("\n" if lines else "no skill matches\n")


SKILL_LINK = re.compile(r"\]\((?!https?:|#|mailto:)([^)\s]+)\)|`((?:references|scripts|templates|assets|examples)/[^`\s]+)`")


def get(home: Path, catalog: dict, sid: str, licenses: dict, log=print) -> Path:
    """Fetch one skill folder at its pin (blobless mirror, only that folder's blobs), check its links, record its
    license. Policy-flagged skills are refused."""
    from .update.track import mirror
    entry = next((e for e in catalog["skills"] if e["id"] == sid), None)
    if entry is None:
        raise KeyError(f"no skill {sid!r} in the catalog (try `agylite skills search`)")
    if entry["policy"]:
        raise PermissionError(f"{sid} carries {', '.join(entry['policy'])}; Agylite does not fetch it (policy)")
    folder = entry["path"].rsplit("/", 1)[0] if "/" in entry["path"] else ""
    dest = home / "cache" / "skills" / entry["repo"] / entry["name"]
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    mp = mirror(home, entry["repository"])
    with __import__("tempfile").TemporaryDirectory() as work:
        subprocess.run(["git", f"--git-dir={mp}", f"--work-tree={work}", "checkout", entry["pin"], "--",
                        folder or "SKILL.md"], check=True, capture_output=True, text=True, timeout=600)
        shutil.copytree(Path(work) / folder if folder else Path(work), dest, dirs_exist_ok=True)
    text = (dest / "SKILL.md").read_text(encoding="utf-8", errors="replace")
    dangling = sorted({m.group(1) or m.group(2) for m in SKILL_LINK.finditer(text)
                       if not (dest / (m.group(1) or m.group(2)).split("#", 1)[0]).exists()})
    lic = licenses.get(entry["repo"], {})
    (dest / ".agylite-provenance.json").write_text(json.dumps({
        "id": sid, "repository": entry["repository"], "commit": entry["pin"], "path": entry["path"],
        "license": lic.get("license"), "attribution": lic.get("attribution"), "dangling_links": dangling},
        indent=1), encoding="utf-8")
    if dangling:
        log(f"note: {len(dangling)} link(s) leave the skill folder and were not fetched: {', '.join(dangling[:5])}")
    return dest
