"""Context loader: every context read goes through here (spec §16–17).

- A per-bundle **context index** (file kind, name, description, sections with token estimates) is built once per
  bundle id under `$AGYLITE_HOME/cache/context-index/` so section choice needs no file read.
- Reads are logged (path, level, bytes, est. tokens, cache hit/miss): the load log is the evidence for budgets and,
  in P11, for isolation.
- With a session id, content already sent in this session is replaced by a short marker (cache hit, no reread).
"""
import json
import os
from pathlib import Path

from ..isolation import atomic
from ..isolation.guard import guard_for
from .cache import SessionCache
from .sections import Section, est_tokens, frontmatter, split_sections

CONTEXT_INDEX_VERSION = 1
LICENSE_PREFIXES = ("LICENSE", "NOTICE", "COPYING", "ACKNOWLEDGEMENTS")
MARKDOWN = (".md", ".mdx")
TEXT = MARKDOWN + (".tmpl", ".txt", ".yaml", ".yml", ".json", ".csv", ".toml",
                   ".sh", ".bash", ".py", ".js", ".mjs", ".cjs", ".ts", ".go", ".rb", ".ps1")
DEEP_DIRS = {"references", "reference", "examples", "example", "templates", "template", "assets", "sections", "docs",
             "data", "playbooks", "rules"}


class ContextError(RuntimeError):
    pass


def file_kind(path: str) -> str:
    """skill / doc (L2-eligible) · reference (L3) · data (listed only) · license · binary."""
    parts = path.split("/")
    name = parts[-1]
    if name.upper().startswith(LICENSE_PREFIXES):
        return "license"
    if name in ("SKILL.md", "SKILL.md.tmpl"):
        return "skill"
    suffix = os.path.splitext(name)[1].lower()
    if suffix not in TEXT:
        return "binary"
    if suffix not in MARKDOWN:
        return "data"
    if any(p.lower() in DEEP_DIRS for p in parts[2:-1]):
        return "reference"
    return "doc"


def _describe(path: str, text: str):
    meta, body = frontmatter(text)
    name = str(meta.get("name") or "").strip()
    desc = " ".join(str(meta.get("description") or "").split())
    if not name:
        for line in text[body:].splitlines():
            if line.startswith("#"):
                name = line.lstrip("#").strip()
                break
    parts = path.split("/")
    return name or (parts[-2] if parts[-1].startswith("SKILL.md") else parts[-1]), desc[:300]


def build_context_index(bundle_dir: Path):
    index = json.loads((bundle_dir / "index.json").read_text(encoding="utf-8"))
    out = {}
    for cid, paths in index["capabilities"].items():
        entries = []
        for p in paths:
            meta = index["files"][p]
            kind = file_kind(p)
            entry = {"path": p, "kind": kind, "bytes": meta["bytes"], "sha256": meta["sha256"],
                     "tokens": est_tokens(meta["bytes"])}
            if kind in ("skill", "doc", "reference"):
                text = (bundle_dir / p).read_text(encoding="utf-8", errors="replace")
                entry["name"], entry["description"] = _describe(p, text)
                entry["sections"] = [s.as_dict() for s in split_sections(text)]
            entries.append(entry)
        out[cid] = entries
    return {"version": CONTEXT_INDEX_VERSION, "bundle_id": index["bundle_id"], "capabilities": out}


def load_context_index(bundle_dir: Path, home: Path):
    """The bundle's context index, built on first use and cached per bundle id (bundles are immutable)."""
    bundle_id = bundle_dir.name
    path = home / "cache" / "context-index" / f"{bundle_id}.json"
    if path.is_file():
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("version") == CONTEXT_INDEX_VERSION and data.get("bundle_id") == bundle_id:
            return data
    data = build_context_index(bundle_dir)
    atomic.write_text(path, json.dumps(data))
    return data


class ContextLoader:
    """Reads files for one assembly, through the session cache when a session id is given."""

    def __init__(self, project=None, session_id: str | None = None, bundle_dir: Path | None = None,
                 home: Path | None = None, use_cache: bool = True):
        self.project = project
        self.session_id = session_id
        self.bundle_dir = bundle_dir
        self.home = home or (project.home if project is not None else None)
        self.log = []
        self.cache = None
        # P11: every read is checked against this project's allowed roots (no cross-project reads, doc 14 §4).
        self.guard = guard_for(project, bundle_dir) if project is not None else None
        if project is not None and session_id and use_cache:
            self.cache = SessionCache(project.data_dir / "sessions" / session_id / "context-cache.json",
                                      project.project_id, session_id)
        self._index = None

    # ── bundle ──────────────────────────────────────────────────────────────────────────────────────────────────
    def require_bundle(self) -> Path:
        if self.bundle_dir is None or not (self.bundle_dir / "index.json").is_file():
            raise ContextError("no capability bundle is installed (run scripts/install or `agylite bundle build`)")
        return self.bundle_dir

    @property
    def index(self):
        if self._index is None:
            bundle = self.require_bundle()
            self._index = load_context_index(bundle, self.home or bundle.parent.parent)
        return self._index

    def files_of(self, cid: str):
        return self.index["capabilities"].get(cid, [])

    def bundle_entry(self, path: str):
        for entries in self.index["capabilities"].values():
            for e in entries:
                if e["path"] == path:
                    return e
        return None

    # ── reads ───────────────────────────────────────────────────────────────────────────────────────────────────
    def cached(self, key: str, *, sha256=None, stat=None, sections=()):
        return bool(self.cache and self.cache.hit(key, sha256=sha256, stat=stat, sections=sections))

    def read(self, path: Path, *, display: str, level: str):
        """Read one file (a cache miss) and log it."""
        if self.guard is not None:
            path = self.guard.check(path)
        text = path.read_text(encoding="utf-8", errors="replace")
        size = len(text.encode("utf-8"))
        self.log.append({"path": display, "level": level, "bytes": size, "est_tokens": est_tokens(size),
                         "cache": "miss"})
        return text

    def note_hit(self, display: str, level: str, sections=()):
        self.log.append({"path": display, "level": level, "bytes": 0, "est_tokens": 0, "cache": "hit",
                         "sections": list(sections)})

    def record(self, key: str, *, level: str, sha256=None, stat=None, sections=(), sent_bytes: int = 0):
        """After a miss: note what was actually sent and remember it for this session."""
        if self.log and self.log[-1]["cache"] == "miss":
            self.log[-1]["sent_bytes"] = sent_bytes
            self.log[-1]["sent_tokens"] = est_tokens(sent_bytes)
            self.log[-1]["sections"] = list(sections)
        if self.cache:
            self.cache.record(key, level=level, sha256=sha256, stat=stat, sections=sections)

    def finish(self, active_capabilities=None):
        if self.project is not None and self.log:
            from ..events.log import emit
            from ..events.used import upstream_counts
            emit(self.project, "CONTEXT_LOADED", session_id=self.session_id,
                 capabilities=active_capabilities or [], bytes_loaded=sum(e["bytes"] for e in self.log),
                 est_tokens=sum(e.get("sent_tokens", 0) for e in self.log),
                 details={"files": len(self.log), "cache_hits": sum(e["cache"] == "hit" for e in self.log),
                          "levels": sorted({e["level"] for e in self.log}),
                          "upstreams": upstream_counts(e["path"] for e in self.log)})
        if self.cache:
            if active_capabilities is not None:
                self.cache.set_active(active_capabilities)
            for item in self.log:
                self.cache.log(item)
            self.cache.save()


def sections_from(entry):
    return [Section(**s) for s in entry.get("sections") or []]
