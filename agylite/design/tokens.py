"""Design-token checks (P14, spec §27 inspectable anti-slop criteria, A-1: local tests instead of screenshot review).

Scans the project's style sources (CSS/SCSS/LESS, JS/TS theme and component files, Tailwind config) for literal colors,
corner radii and font families, and checks them against limits (config/design.yaml). A design that keeps to one
accent, one grey family, a small radius scale and few font families reads as intentional; drift shows up as counts.
Results are PASS / WARN / FAIL with the values found and where, so they can be recorded as evidence.
"""
import colorsys
import os
import re
from pathlib import Path

import yaml

from ..codebase.structural import SKIP_DIRS
from ..paths import repo_root

STYLE_EXT = {".css", ".scss", ".sass", ".less", ".ts", ".tsx", ".js", ".jsx", ".vue", ".svelte", ".html", ".mjs"}
MAX_FILES = 5000
MAX_BYTES = 256 * 1024
HEX = re.compile(r"(?<![\w&])#([0-9a-fA-F]{6}|[0-9a-fA-F]{3})\b")
RGB = re.compile(r"rgba?\(\s*(\d{1,3})[\s,]+(\d{1,3})[\s,]+(\d{1,3})")
RADIUS = re.compile(r"(?:border-radius|borderRadius|rounded)\s*[:=]\s*['\"]?([0-9.]+(?:px|rem|em|%)?)")
FONT = re.compile(r"(?:font-family|fontFamily)\s*[:=]\s*['\"\[]?\s*['\"]?([A-Za-z][\w \-]+)")
GENERIC_FONTS = {"sans-serif", "serif", "monospace", "system-ui", "inherit", "ui-sans-serif", "ui-monospace",
                 "ui-serif", "cursive", "initial", "var"}


def load_limits(root: Path | None = None) -> dict:
    with open((root or repo_root()) / "config" / "design.yaml", encoding="utf-8") as f:
        return (yaml.safe_load(f) or {})["limits"]


def _rgb_hex(h: str):
    h = h if len(h) == 6 else "".join(c * 2 for c in h)
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def classify_color(rgb, limits) -> str:
    r, g, b = (c / 255 for c in rgb)
    hue, light, sat = colorsys.rgb_to_hls(r, g, b)
    if light <= 0.06 or light >= 0.96:
        return "neutral-extreme"   # near black / near white: not counted
    if sat < limits["grey_max_saturation"]:
        return "grey"
    return "accent"


def _hue_bucket(rgb, size) -> int:
    h, _l, _s = colorsys.rgb_to_hls(*(c / 255 for c in rgb))
    return int(h * 360 // size)


def _files(root: Path):
    n = 0
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS and not d.startswith("."))
        for name in sorted(filenames):
            p = Path(dirpath) / name
            if p.suffix.lower() in STYLE_EXT or name.startswith("tailwind.config"):
                if "test" in name or "spec" in name or p.is_symlink():
                    continue
                yield p
                n += 1
                if n >= MAX_FILES:
                    return


def scan(root: Path):
    found = {"colors": {}, "radii": {}, "fonts": {}}
    for p in _files(root):
        try:
            text = p.read_bytes()[:MAX_BYTES].decode("utf-8", errors="ignore")
        except OSError:
            continue
        rel = p.relative_to(root).as_posix()
        for m in HEX.finditer(text):
            found["colors"].setdefault(_rgb_hex(m.group(1)), set()).add(rel)
        for m in RGB.finditer(text):
            rgb = tuple(min(int(x), 255) for x in m.groups())
            found["colors"].setdefault(rgb, set()).add(rel)
        for m in RADIUS.finditer(text):
            v = m.group(1)
            if v not in ("0", "0px"):
                found["radii"].setdefault(v, set()).add(rel)
        for m in FONT.finditer(text):
            fam = m.group(1).strip().strip("'\"").lower()
            if fam and fam.split()[0] not in GENERIC_FONTS and not fam.startswith("var"):
                found["fonts"].setdefault(fam, set()).add(rel)
    return found


def design_md_overrides(root: Path) -> dict:
    """`design_check_overrides` from DESIGN.md front matter (MP4 §2.3): integer limits an approved design needs."""
    path = Path(root) / "DESIGN.md"
    text = path.read_text(encoding="utf-8") if path.is_file() else ""
    if not text.startswith("---"):
        return {}
    try:
        fm = yaml.safe_load(text.split("---", 2)[1]) or {}
    except yaml.YAMLError:
        return {}
    raw = fm.get("design_check_overrides") or {}
    return {k: v for k, v in raw.items() if isinstance(v, int) and not isinstance(v, bool)} if isinstance(raw, dict) else {}


def check(root: Path, limits=None) -> dict:
    limits = dict(limits or load_limits())
    applied = {k: v for k, v in design_md_overrides(root).items() if k in limits and v > limits[k]}   # raise only
    limits.update(applied)
    found = scan(root)
    accents, greys = {}, {}
    for rgb, where in found["colors"].items():
        kind = classify_color(rgb, limits)
        if kind == "accent":
            accents.setdefault(_hue_bucket(rgb, limits["hue_bucket_degrees"]), []).append(("#%02x%02x%02x" % rgb, where))
        elif kind == "grey":   # pure neutrals (no tint) fit any family; tinted greys define the families
            tinted = colorsys.rgb_to_hls(*(c / 255 for c in rgb))[2] > 0.02
            key = _hue_bucket(rgb, limits["hue_bucket_degrees"]) if tinted else None
            greys.setdefault(key, []).append("#%02x%02x%02x" % rgb)

    def result(name, count, limit, values, why):
        status = "PASS" if count <= limit else ("WARN" if count <= limit * 2 else "FAIL")
        return {"check": name, "status": status, "count": count, "limit": limit, "values": values[:12], "why": why}

    checks = [
        result("accent hues", len(accents), limits["accent_hues"],
               [v[0][0] for v in accents.values()], "One deliberate accent (two at most) reads as a brand, not a palette"),
        result("grey families", len([k for k in greys if k is not None]) or (1 if greys else 0), limits["grey_families"],
               [v[0] for v in greys.values()], "Mixing cool and warm greys reads as unintentional"),
        result("corner radii", len(found["radii"]), limits["radius_values"], sorted(found["radii"]),
               "Radii should come from a small scale"),
        result("font families", len(found["fonts"]), limits["font_families"], sorted(found["fonts"]),
               "Display + body (+ mono) is enough"),
    ]
    status = "FAIL" if any(c["status"] == "FAIL" for c in checks) else (
        "WARN" if any(c["status"] == "WARN" for c in checks) else "PASS")
    return {"status": status, "checks": checks, "design_md": (root / "DESIGN.md").is_file(),
            "colors_found": len(found["colors"]), "overrides": applied}
