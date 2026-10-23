"""The global verification policy (`config/verification.yaml`, D-049 superseding D-035) and its diagnostics.

One policy for every project and host: tests, types, lint and build for every change, AND a browser check (`agylite
verify --browser`) for UI and website work. Only the simulator recording loop stays disabled.
"""
from pathlib import Path

import yaml

from ..paths import repo_root

MODE = "tests-and-browser"
MUST_BE_DISABLED = ("simulator_recording_loop",)


def load_policy(root: Path | None = None):
    with open((root or repo_root()) / "config" / "verification.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def state_block(cfg):
    """The policy part of a project's `state.yaml` verification block (spec: verification mode + disabled switches)."""
    off = cfg.get("disabled") or {}
    return {"mode": cfg.get("mode"), "browser_verification": "enabled" if cfg.get("browser_verification") else "disabled",
            "simulator_recording_loop": "disabled" if off.get("simulator_recording_loop") else "enabled"}


def policy_problems(cfg, cards):
    """Policy violations: wrong mode, a switched-on disabled mechanism, no browser_verification section, or a
    disabled-by-policy capability that is enabled (diagnostics, spec §41)."""
    p = []
    if cfg.get("mode") != MODE:
        p.append(f"verification mode is {cfg.get('mode')!r}; policy requires {MODE}")
    off = cfg.get("disabled") or {}
    p += [f"verification policy: {k} must be disabled" for k in MUST_BE_DISABLED if off.get(k) is not True]
    if not cfg.get("browser_verification"):
        p.append("verification policy: browser_verification (D-049) is missing")
    for cid, card in cards.items():
        if card.get("runtime_status") == "DISABLED_BY_POLICY" and card.get("enabled"):
            p.append(f"{cid}: DISABLED_BY_POLICY capability is enabled")
        if card.get("web_qa_class") == "DISABLED_BY_POLICY" and card.get("runtime_status") != "DISABLED_BY_POLICY":
            p.append(f"{cid}: web_qa_class DISABLED_BY_POLICY needs runtime_status DISABLED_BY_POLICY")
    return p
