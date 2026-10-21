"""Upstream tracking (P28, D-047): find new upstream commits, fetch only those, and apply them through the checked
update pipeline on a schedule (`config/upstreams.yaml`).

- check:   `git ls-remote` per upstream (seconds, no download) → newest commit vs the active pin.
- mirrors: one blobless bare mirror per upstream in `$AGYLITE_HOME/mirrors/`; later runs fetch only new commits and the
           update clones from the local mirror, so only the bundled files of the new commit are downloaded.
- latest:  each due upstream with a new commit → `update()`; one failure never blocks the others.
- promote: copy the active bundle's pins and inventories into the repository's audited evidence (CI pull requests).
- schedule: an optional weekly macOS LaunchAgent running `agylite update --latest --due` (explicit opt-in).
"""
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

from ..paths import repo_root
from .core import UpdateError, _current_evidence, _pins, update

INTERVAL = {"weekly": timedelta(days=7), "monthly": timedelta(days=30)}
VERSION_TAG = re.compile(r"^v?(\d+)\.(\d+)(?:\.(\d+))?$")
LAUNCH_LABEL = "com.agylite.update"


def base_url() -> str:
    """Where upstreams live; tests point this at local repositories."""
    return os.environ.get("AGYLITE_UPSTREAM_BASE", "https://github.com").rstrip("/")


def url_for(repo: str) -> str:
    return f"{base_url()}/{repo}.git"


def load_policy(root: Path | None = None) -> dict:
    cfg = yaml.safe_load(((root or repo_root()) / "config" / "upstreams.yaml").read_text(encoding="utf-8"))
    default = cfg.get("default", {"track": "weekly"})
    return {name: {**default, **(entry or {})} for name, entry in (cfg.get("upstreams") or {}).items()}


def _git(*args, cwd=None, timeout=120):
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, timeout=timeout, check=True).stdout


def remote_latest(repo: str, policy: dict) -> str:
    """Newest commit of the tracked branch, or of the highest version tag for `releases`."""
    if policy.get("track") == "releases":
        best, sha = None, None
        for line in _git("ls-remote", "--tags", url_for(repo)).splitlines():
            ref_sha, ref = line.split("\t")
            name = ref.rsplit("/", 1)[-1]
            peeled = name.endswith("^{}")
            m = VERSION_TAG.match(name.removesuffix("^{}"))
            if m:
                key = tuple(int(x or 0) for x in m.groups())
                if best is None or key > best or (key == best and peeled):
                    best, sha = key, ref_sha
        if sha is None:
            raise UpdateError(f"{repo}: no version tags to track")
        return sha
    out = _git("ls-remote", url_for(repo), f"refs/heads/{policy.get('branch', 'main')}").split()
    if not out:
        raise UpdateError(f"{repo}: branch {policy.get('branch', 'main')} not found")
    return out[0]


def _state_path(home: Path) -> Path:
    return Path(home) / "updates" / "tracking.json"


def _state(home: Path) -> dict:
    p = _state_path(home)
    return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else {}


def _save_state(home: Path, data: dict):
    p = _state_path(home)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=1, sort_keys=True) + "\n", encoding="utf-8")


def due(name: str, policy: dict, state: dict, now=None) -> bool:
    track = policy.get("track", "weekly")
    if track == "manual":
        return False
    last = (state.get(name) or {}).get("applied_check")
    if not last:
        return True
    interval = INTERVAL.get(track, INTERVAL["weekly"])
    return (now or datetime.now(timezone.utc)) - datetime.fromisoformat(last) >= interval


def _baseline(home: Path, evidence: Path | None) -> Path:
    """The active bundle's own pins win once an update has been applied; `evidence` is only the starting baseline."""
    own = Path(home) / "bundles" / "current" / "evidence"
    return own if own.is_dir() else (Path(evidence) if evidence else _current_evidence(Path(home)))


def check(home: Path, *, evidence: Path | None = None, policy=None, repos=None) -> list:
    """Every tracked upstream: pinned commit, newest remote commit, policy, and whether an update is waiting."""
    evidence = _baseline(home, evidence)
    pins, policy = _pins(evidence), policy or load_policy()
    state, rows = _state(home), []
    for name in sorted(repos or pins):
        pol = policy.get(name, {"track": "weekly", "branch": "main"})
        row = {"repo": name, "upstream": pins[name]["repo"], "track": pol.get("track"), "pinned": pins[name]["head"]}
        try:
            latest = remote_latest(pins[name]["repo"], pol)
            row.update(latest=latest, status="up-to-date" if latest == pins[name]["head"] else "update-available")
        except (subprocess.SubprocessError, UpdateError, OSError) as exc:
            row.update(latest=None, status="error", error=str(exc).strip()[-200:])
        row["due"] = due(name, pol, state)
        rows.append(row)
    # Doctor counts a pin as fresh from the last check that found it current (MP1 F9); `due` is unaffected.
    current = [r["repo"] for r in rows if r["status"] == "up-to-date"]
    if current:
        stamp = datetime.now(timezone.utc).isoformat()
        for name in current:
            state.setdefault(name, {})["checked_current"] = stamp
        _save_state(home, state)
    return rows


def mirror(home: Path, repo: str) -> Path:
    """Blobless bare mirror; the first call clones, later calls fetch only new commits."""
    path = Path(home) / "mirrors" / (repo.replace("/", "__") + ".git")
    if (path / "HEAD").is_file():
        _git("fetch", "--quiet", "--filter=blob:none", "--prune", "origin",
             "+refs/heads/*:refs/heads/*", "+refs/tags/*:refs/tags/*", cwd=path, timeout=600)
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        _git("clone", "--quiet", "--bare", "--filter=blob:none", url_for(repo), str(path), timeout=600)
    return path


def commits_between(mirror_path: Path, old: str, new: str) -> int | None:
    try:
        return int(_git("rev-list", "--count", f"{old}..{new}", cwd=mirror_path).strip())
    except subprocess.SubprocessError:
        return None


def latest(home: Path, *, only_due=False, repos=None, tracks=None, policy=None, staging=None, evidence=None,
           rules_path=None, licenses_path=None, check_registry=True, log=print) -> list:
    """Apply new upstream commits one repository at a time; each switch is independent and reversible."""
    home = Path(home)
    policy = policy or load_policy()
    state = _state(home)
    now = datetime.now(timezone.utc)
    results = []
    for row in check(home, evidence=evidence, policy=policy, repos=repos):
        name = row["repo"]
        pol = policy.get(name, {})
        if (row["status"] == "error" or (only_due and not row["due"]) or (pol.get("track") == "manual" and not repos)
                or (tracks and pol.get("track") not in tracks)):
            results.append({**row, "action": "skipped"})
            continue
        if row["status"] == "up-to-date":
            state.setdefault(name, {})["applied_check"] = now.isoformat()
            results.append({**row, "action": "none"})
            continue
        try:
            mp = mirror(home, row["upstream"])
            row["commits"] = commits_between(mp, row["pinned"], row["latest"])
            report = update(home, name, row["latest"], mirror_path=mp, staging=staging,
                            evidence=_baseline(home, evidence), rules_path=rules_path,
                            licenses_path=licenses_path, self_test=bool(pol.get("self_test")),
                            check_registry=check_registry, log=log)
        except (UpdateError, subprocess.SubprocessError, OSError) as exc:
            report = {"status": "failed", "errors": [str(exc).strip()[-300:]]}
        if report.get("status") == "activated":
            state.setdefault(name, {}).update(applied_check=now.isoformat(), applied=row["latest"])
        results.append({**row, "action": report.get("status"), "bundle_id": report.get("bundle_id"),
                        "diff": report.get("diff"), "errors": report.get("errors", [])[:5]})
    _save_state(home, state)
    return results


def promote(home: Path, target: Path | None = None) -> list:
    """Copy the active bundle's pins and inventories into the repository's audited evidence (for a reviewed PR)."""
    src = Path(home) / "bundles" / "current" / "evidence"
    if not src.is_dir():
        raise UpdateError("the active bundle has no evidence of its own (no update applied)")
    target = target or repo_root() / "docs" / "audit" / "evidence"
    old = yaml.safe_load((target / "upstream-staging-snapshot.yaml").read_text(encoding="utf-8"))["snapshots"]
    new = yaml.safe_load((src / "upstream-staging-snapshot.yaml").read_text(encoding="utf-8"))["snapshots"]
    changed = [n for n in new if new[n]["head"] != old.get(n, {}).get("head")]
    text = (target / "upstream-staging-snapshot.yaml").read_text(encoding="utf-8")
    for n in changed:   # edit the pin in place so the file's comments and layout stay intact
        text = text.replace(old[n]["head"], new[n]["head"])
        shutil.copy2(src / "upstream-file-hashes" / f"{n}.tsv", target / "upstream-file-hashes" / f"{n}.tsv")
    (target / "upstream-staging-snapshot.yaml").write_text(text, encoding="utf-8")
    return changed


def launch_agent_plist(program: str, home: Path) -> str:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>{LAUNCH_LABEL}</string>
  <key>ProgramArguments</key>
  <array><string>{program}</string><string>update</string><string>--latest</string><string>--due</string></array>
  <key>EnvironmentVariables</key><dict><key>AGYLITE_HOME</key><string>{home}</string></dict>
  <key>StartCalendarInterval</key><dict><key>Weekday</key><integer>1</integer><key>Hour</key><integer>9</integer><key>Minute</key><integer>0</integer></dict>
  <key>StandardOutPath</key><string>{home}/updates/scheduled.log</string>
  <key>StandardErrorPath</key><string>{home}/updates/scheduled.log</string>
</dict>
</plist>
"""


def schedule(home: Path, enable: bool, user_home: Path | None = None, load=True) -> Path:
    """Opt-in weekly job (Mondays 09:00) via a LaunchAgent; `remove` unloads and deletes it. macOS only."""
    agents = (user_home or Path.home()) / "Library" / "LaunchAgents"
    plist = agents / f"{LAUNCH_LABEL}.plist"
    if enable:
        program = shutil.which("agylite") or str(Path(sys.executable).with_name("agylite"))
        agents.mkdir(parents=True, exist_ok=True)
        plist.write_text(launch_agent_plist(program, Path(home)), encoding="utf-8")
        if load and sys.platform == "darwin":
            subprocess.run(["launchctl", "load", "-w", str(plist)], capture_output=True)
    elif plist.exists():
        if load and sys.platform == "darwin":
            subprocess.run(["launchctl", "unload", "-w", str(plist)], capture_output=True)
        plist.unlink()
    return plist
