"""Diagram verification (MP5 §3.3, config/verification.yaml `diagram_verification`, owner approval 2026-10-22): a
delivered Archify diagram is checked again with Archify's own deterministic gates — strict provenance `check` and the
headless Chrome `browser-check` — whenever it changed (a path under `.archify/`) or is named with `--diagram`.
The browser-check runs whenever Chrome is present; without Chrome it is NOT_RUN (BLOCKED), never a pass. Its receipts
and screenshots are evidence with their sha256.
"""
import sys
from pathlib import Path

from ..runtimes import archify
from .detect import Check

FOLDER = ".archify"
RECEIPTS = (".browser-check.json", ".delivery.json", ".finalize.json", ".finalize-summary.json")


def outputs(root: Path, changed=(), named=()) -> list:
    """Delivered diagram pages to check: the named ones, plus every page in a changed `.archify/<folder>/`."""
    root = Path(root)
    pages = [Path(p) if Path(p).is_absolute() else root / p for p in named or []]
    folders = set()
    for p in changed or []:
        parts = Path(p).parts
        if FOLDER in parts:
            i = parts.index(FOLDER)
            if len(parts) > i + 1:
                folders.add(root.joinpath(*parts[: i + 2]))
    for folder in sorted(folders):
        pages += sorted(h for h in folder.glob("*.html") if folder.is_dir())
    seen, out = set(), []
    for page in pages:
        if page.is_file() and page not in seen:
            seen.add(page)
            out.append(page)
    return out


def checks(project, changed, *, named=None) -> list:
    """[(Check, argv or None, reason, tests)] for each page: check, then browser-check (or NOT_RUN without Chrome)."""
    pages = outputs(project.root, changed, named)
    if not pages:
        return []
    cli = [sys.executable, "-m", "agylite.cli", "diagram", "--project", str(project.root)]
    chrome = archify.find_chrome()
    out = []
    for page in pages:
        rel = page.relative_to(project.root).as_posix() if page.is_relative_to(project.root) else str(page)
        why = f"diagram {rel}"
        out.append((Check("diagram", "archify check", [], "node"),
                    cli + ["check", str(page), "--json", "--require-provenance"], why, []))
        if chrome:
            out.append((Check("diagram", "archify browser-check", [], "node"),
                        cli + ["browser-check", str(page), "--json", "--require-provenance"], why, []))
        else:
            out.append((Check("diagram", "archify browser-check", [], "node",
                              notes=["NOT_RUN: browser-check (chrome missing; set ARCHIFY_CHROME)"]), None, why, []))
    return out


def result(project_root: Path, reason: str) -> dict:
    """Receipts and screenshots next to the checked page, with sha256 (artefacts beside the passing command)."""
    rel = reason.removeprefix("diagram ")
    page = Path(project_root) / rel
    arts = archify.receipts(page) if page.is_file() else []
    for a in arts:
        p = Path(a["path"])
        a["path"] = p.relative_to(project_root).as_posix() if p.is_relative_to(project_root) else str(p)
    return {"artifacts": arts}
