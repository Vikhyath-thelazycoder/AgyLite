"""`agylite design extract` (MP4 §2.3–2.4): 1-3 inspiration URLs → one DESIGN.md the owner approves before UI code.

Per URL designlang writes its own output (`<out>/<host>/`, incl. `<host>-DESIGN.md`, 8 sections + YAML front matter).
Two URLs: also `designlang pair` (its comparison card) and a fused DESIGN.md made by designlang's own `fuseDesigns`
and DESIGN.md formatter (`fuse_design_md.mjs`). Three URLs: the primary is paired with the second; the third site's
values go to MERGE_NOTES.md for the owner (designlang has no three-way fuse, and none is invented here).

Systems, never identity (§2.4): the primary colour (the inspiration's brand colour) is shifted ≥ 20° in hue and the
change is written to MERGE_NOTES.md. Credentials never reach designlang (`--smart` can never trigger). An existing
DESIGN.md is never replaced without `replace=True` (precedence rule 2): the result goes to
docs/design/DESIGN.inspiration.md instead. Front matter gains `sources`, `mode: inspiration` and, when the extracted
system needs more than config/design.yaml allows, `design_check_overrides`.
"""
import colorsys
import ipaddress
import re
import subprocess
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

import yaml

MAX_URLS = 3
DEFAULT_OUT = Path(".agylite/design/inspiration")
DESIGN_MD_SECTIONS = ("Overview", "Colors", "Typography", "Layout", "Elevation and Depth", "Shapes", "Components",
                      "Do's and Don'ts")
AXES = ("colors_from", "typography_from", "spacing_from", "shape_from", "motion_from", "voice_from", "components_from")
SECRET = re.compile(r"(^OPENAI_|^ANTHROPIC_|^ATLASCLOUD|^ATLAS_CLOUD|KEY|TOKEN|SECRET|PASSWORD|CREDENTIAL)", re.I)
HUE_SHIFT = 24
FUSE_SCRIPT = Path(__file__).with_name("fuse_design_md.mjs")


class ExtractError(ValueError):
    pass


def host_of(url: str) -> str:
    return (urlparse(url).hostname or "site").removeprefix("www.")


def validate_urls(urls, allow_local=False) -> list:
    if not urls:
        raise ExtractError("give 1-3 inspiration URLs")
    if len(urls) > MAX_URLS:
        raise ExtractError(f"at most {MAX_URLS} inspiration URLs ({len(urls)} given)")
    out = []
    for raw in urls:
        url = raw if "://" in raw else f"https://{raw}"
        p = urlparse(url)
        if p.scheme not in ("http", "https") or not p.hostname:
            raise ExtractError(f"{raw}: only http(s) URLs")
        host = p.hostname.lower()
        local = host == "localhost" or host.endswith((".local", ".localhost", ".internal"))
        try:
            ip = ipaddress.ip_address(host)
            local = local or ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved
        except ValueError:
            pass
        if local and not allow_local:
            raise ExtractError(f"{raw}: local or private address (pass --allow-local for your own dev server)")
        out.append(url)
    return out


def child_env(base: dict, runtime_env: dict) -> dict:
    env = {k: v for k, v in base.items() if not SECRET.search(k)}
    env.update(runtime_env)
    return env


def _axis_flags(axes):
    return [x for k, v in (axes or {}).items() if v for x in (f"--{k.replace('_', '-')}", v)]


def step_kind(argv) -> str:
    return "fuse" if any(str(a).endswith(FUSE_SCRIPT.name) for a in argv) else ("pair" if argv[1] == "pair" else "site")


def plan(urls, out: Path, runtime, *, primary=None, dark=False, depth=None, axes=None) -> list:
    steps = []
    for url in urls:
        argv = [runtime.bin, url, "--out", str(out / host_of(url))]
        argv += ["--dark"] if dark else []
        argv += ["--depth", str(depth)] if depth else []
        steps.append(argv)
    if len(urls) >= 2:
        a = primary or urls[0]
        b = next(u for u in urls if u != a)
        steps.append([runtime.bin, "pair", a, b, "--format", "all", "--out", str(out / "pair"), *_axis_flags(axes)])
        steps.append([runtime.node, str(FUSE_SCRIPT), "--pkg", str(runtime.pkg), "--a", a, "--b", b,
                      "--out", str(out / "pair" / "FUSED-DESIGN.md"), *_axis_flags(axes)])
    return steps


def _split(md: str):
    if not md.startswith("---"):
        return {}, md
    _, fm, body = md.split("---", 2)
    return yaml.safe_load(fm) or {}, body.lstrip("\n")


def hue_distance(a: str, b: str) -> float:
    ha, hb = (colorsys.rgb_to_hls(*_rgb(x))[0] * 360 for x in (a, b))
    d = abs(ha - hb) % 360
    return min(d, 360 - d)


def _rgb(hex_):
    h = hex_.lstrip("#")
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))


def shift_hue(hex_: str, degrees=HUE_SHIFT) -> str:
    hue, light, sat = colorsys.rgb_to_hls(*_rgb(hex_))
    r, g, b = colorsys.hls_to_rgb((hue + degrees / 360) % 1, light, sat)
    return "#%02x%02x%02x" % tuple(round(c * 255) for c in (r, g, b))


def _overrides(tokens, limits):
    out = {}
    radii = [v for v in (tokens.get("radii") or {}).values() if v]
    if len(radii) > limits["radius_values"]:
        out["radius_values"] = len(radii)
    fonts = {v for k, v in (tokens.get("typography") or {}).items() if k in ("sans", "serif", "display", "mono") and v}
    if len(fonts) > limits["font_families"]:
        out["font_families"] = len(fonts)
    return out


def _tokens_row(fm):
    t = fm.get("tokens") or {}
    return {"palette": ", ".join(str(v) for v in (t.get("colors") or {}).values()),
            "type": ", ".join(str(v) for v in (t.get("typography") or {}).values()),
            "spacing": str((t.get("spacing") or {}).get("base", "—")),
            "radii": ", ".join(str(v) for v in (t.get("radii") or {}).values()) or "—",
            "motion": str(t.get("motion") or "—")}


def run(root: Path, urls, *, runtime, runner=None, out=None, primary=None, dark=False, depth=None, axes=None,
        replace=False, allow_local=False, base_env=None, limits=None) -> dict:
    import os

    from .tokens import load_limits
    urls = validate_urls(urls, allow_local)
    if primary and primary not in urls:
        primary = validate_urls([primary], allow_local)[0]
    root = Path(root)
    out_dir = root / (out or DEFAULT_OUT)
    out_dir.mkdir(parents=True, exist_ok=True)
    env = child_env(dict(base_env if base_env is not None else os.environ), runtime.env())
    runner = runner or (lambda argv, e, cwd: subprocess.run(argv, env=e, cwd=cwd).returncode)
    for argv in plan(urls, out_dir, runtime, primary=primary, dark=dark, depth=depth, axes=axes):
        code = runner(argv, env, root)
        if code != 0:
            raise ExtractError(f"{step_kind(argv)} step failed (exit {code}): {' '.join(map(str, argv[:4]))}")
    first = primary or urls[0]
    src = (out_dir / "pair" / "FUSED-DESIGN.md") if len(urls) >= 2 else next((out_dir / host_of(first)).glob("*-DESIGN.md"))
    fm, body = _split(src.read_text(encoding="utf-8"))
    tokens = fm.setdefault("tokens", {})
    notes = ["# Inspiration merge notes", "", f"Sources: {', '.join(urls)} (designlang {runtime.version}, {date.today()})", ""]
    primary_hex = (tokens.get("colors") or {}).get("primary")
    if primary_hex and re.fullmatch(r"#[0-9a-fA-F]{6}", str(primary_hex)):
        new = shift_hue(primary_hex)
        tokens["colors"]["primary"] = new
        body = re.sub(re.escape(primary_hex), new, body, flags=re.I)
        notes += ["## Identity (systems, never identity)", "",
                  f"Primary colour {primary_hex} is the inspiration's brand colour; shifted {HUE_SHIFT}° in hue to "
                  f"{new}. Logos, copy, product imagery and trademarked names are not taken.", ""]
    if len(urls) == 3:
        third = next(u for u in urls if u not in (first, next(u for u in urls if u != first)))
        tfm, _ = _split(next((out_dir / host_of(third)).glob("*-DESIGN.md")).read_text(encoding="utf-8"))
        row = _tokens_row(tfm)
        notes += ["## Third site", "", f"{third} is not fused (designlang pairs two sites); its values are listed for "
                  "the owner to pick from.", "", "| axis | value from the third site | taken |", "|---|---|---|"]
        notes += [f"| {k} | {v} | no (owner may pick) |" for k, v in row.items()] + [""]
    overrides = _overrides(tokens, limits or load_limits())
    fm.update(mode="inspiration", sources=[{"url": u, "extracted": str(date.today()), "designlang": runtime.version}
                                            for u in urls])
    if overrides:
        fm["design_check_overrides"] = overrides
    target = root / "DESIGN.md"
    needs_decision = target.exists() and not replace
    if needs_decision:
        target = root / "docs" / "design" / "DESIGN.inspiration.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("---\n" + yaml.safe_dump(fm, sort_keys=False, allow_unicode=True) + "---\n\n" + body,
                      encoding="utf-8")
    (out_dir / "MERGE_NOTES.md").write_text("\n".join(notes) + "\n", encoding="utf-8")
    t = fm["tokens"]
    summary = {"palette": [str(v) for v in (t.get("colors") or {}).values()],
               "fonts": [str(v) for k, v in (t.get("typography") or {}).items() if k != "base"],
               "spacing_base": (t.get("spacing") or {}).get("base"),
               "radii": [v for v in (t.get("radii") or {}).values()]}
    return {"design_md": str(target), "needs_replace_decision": needs_decision, "out": str(out_dir),
            "merge_notes": str(out_dir / "MERGE_NOTES.md"), "overrides": overrides, "summary": summary}
