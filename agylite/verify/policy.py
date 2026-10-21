"""The global verification policy (`config/verification.yaml`, D-035) and its diagnostics.

One policy for every project and host: local test-first; browser visual verification, Chrome DevTools and screenshot
verification are disabled. Projects may only *record* a browser exception in their own state (P11 isolation).
"""
from pathlib import Path

import yaml

from ..paths import repo_root

MODE = "local-test-first"
# MP4 §3.3: browser_visual_verification and screenshot_verification are on for design work (Taste inspect); the rest
# stays off until Phase 7 (IMPLEMENTATION_PLAN §2.2).
MUST_BE_DISABLED = ("chrome_devtools", "screenshot_comparison", "visual_browser_qa", "simulator_recording_loop")


def load_policy(root: Path | None = None):
    with open((root or repo_root()) / "config" / "verification.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def state_block(cfg):
    """The policy part of a project's `state.yaml` verification block (spec: verification mode + disabled switches)."""
    off = cfg.get("disabled") or {}
    return {"mode": cfg.get("mode"),
            "browser_visual_verification": "disabled" if off.get("browser_visual_verification") else "enabled",
            "chrome_devtools": "disabled" if off.get("chrome_devtools") else "enabled",
            "screenshot_verification": "disabled" if off.get("screenshot_verification") else "enabled"}


def policy_problems(cfg, cards):
    """Policy violations: wrong mode, a switched-on mechanism, or an enabled capability that needs a browser outside
    the scoped SEO/media domains (diagnostics, spec §41)."""
    p = []
    if cfg.get("mode") != MODE:
        p.append(f"verification mode is {cfg.get('mode')!r}; policy requires {MODE}")
    off = cfg.get("disabled") or {}
    p += [f"verification policy: {k} must be disabled" for k in MUST_BE_DISABLED if off.get(k) is not True]
    scoped = set(cfg.get("scoped_browser_use") or {})
    for cid, card in cards.items():
        domain = cid.split("/", 1)[0]
        if card.get("enabled") and card.get("requires_browser", "none") != "none" and domain not in scoped:
            p.append(f"{cid}: browser visual verification active but policy requires {MODE}")
        if card.get("runtime_status") == "DISABLED_BY_POLICY" and card.get("enabled"):
            p.append(f"{cid}: DISABLED_BY_POLICY capability is enabled")
        if card.get("web_qa_class") == "DISABLED_BY_POLICY" and card.get("runtime_status") != "DISABLED_BY_POLICY":
            p.append(f"{cid}: web_qa_class DISABLED_BY_POLICY needs runtime_status DISABLED_BY_POLICY")
    return p
