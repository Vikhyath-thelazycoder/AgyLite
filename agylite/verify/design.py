"""Design verification (MP4 §3.3, IMPLEMENTATION_PLAN §2.2): a change that touches style or markup is done only when
`agylite design check`, Taste `lint` on the changed files and Taste `inspect` (0 FAIL, at 1440/768/390) pass, together
with the project's own tests and build — never instead of them. Inspect's screenshots are evidence with their sha256.
A missing node>=22, browser or page is recorded as BLOCKED (NOT_RUN …), never a pass. The rest of the browser policy
(Playwright runtime, `verify --browser`, flows) is Phase 7.
"""
import hashlib
import re
import sys
from pathlib import Path

from ..paths import agylite_home, current_bundle
from ..runtimes import taste
from .detect import Check

STYLE_EXT = {".css", ".scss", ".sass", ".less", ".html", ".htm", ".jsx", ".tsx", ".vue", ".svelte", ".astro", ".mdx"}
PAGES = ("index.html", "dist/index.html", "build/index.html", "out/index.html", "public/index.html")
RESULT = re.compile(r"(\d+)\s+FAIL,\s+(\d+)\s+WARN")
SHOTS = (".png", ".jpg", ".jpeg", ".webp")


def design_files(paths) -> list:
    return [p for p in paths or [] if Path(p).suffix.lower() in STYLE_EXT]


def page(root: Path, given=None):
    if given:
        return given
    return next((str(Path(root) / p) for p in PAGES if (Path(root) / p).is_file()), None)


def checks(project, changed, *, inspect=None, bundle_dir=None, home=None) -> list:
    """[(Check, argv or None, reason, tests)]; argv None means NOT_RUN, recorded as BLOCKED with the Check's note."""
    files = design_files(changed)
    if not files:
        return []
    root = str(project.root)
    cli = [sys.executable, "-m", "agylite.cli"]
    why = f"style/markup changed: {', '.join(files[:5])}"
    h = taste.health(bundle_dir or current_bundle(), home or agylite_home())
    node_ok = str(h.get("node", "")).startswith("node ")
    out = [(Check("design", "design tokens", [], "agylite"), cli + ["design", "check", "--project", root], why, [])]
    if node_ok:
        out.append((Check("design", "taste lint", [], "node"), cli + ["design", "taste", "--project", root, "lint", *files],
                    why, []))
    else:
        out.append((Check("design", "taste lint", [], "node", notes=["NOT_RUN: taste lint (node>=22 missing)"]), None,
                    why, []))
    target = page(project.root, inspect)
    note = ("NOT_RUN: taste inspect (node>=22 missing)" if not node_ok else
            "NOT_RUN: browser (chrome missing)" if h.get("browser") == "missing" else
            "NOT_RUN: taste inspect (no page: pass --inspect <url or file>)" if not target else None)
    if note:
        out.append((Check("design", "taste inspect", [], "node", notes=[note]), None, why, []))
    else:
        out.append((Check("design", "taste inspect", [], "node"),
                    cli + ["design", "taste", "--project", root, "inspect", target], why, []))
    return out


def inspect_result(root: Path, r: dict) -> dict:
    """FAIL/WARN counts from the inspector's RESULT line; any FAIL fails; screenshots with sha256 as artefacts."""
    m = RESULT.search(r.get("output_tail") or "")
    fails, warns = (int(m.group(1)), int(m.group(2))) if m else (None, None)
    shots = Path(root) / ".taste-skill" / "inspect"
    arts = [{"path": p.relative_to(root).as_posix(), "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
            for p in sorted(shots.rglob("*")) if p.suffix.lower() in SHOTS] if shots.is_dir() else []
    upd = {"fails": fails, "warns": warns, "artifacts": arts}
    if fails:
        upd["result"] = "FAILED"
    return upd
