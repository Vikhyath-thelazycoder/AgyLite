"""Opt-in research credentials (MP5 §1.2): X cookies (`auth_token`, `ct0`) and the Reddit session cookie.

Stored in the macOS Keychain when available (`security`, values passed on stdin, never in argv), else in
`~/.agylite/secrets/research.env` (dir 0700, file 0600). Which store holds them is recorded in
`~/.agylite/secrets/research.json` (names only, never values). Values reach only the child process of the one
command that needs them; they are never printed, logged, written into a project, events or evidence.
`AGYLITE_SECRETS_BACKEND=file|keychain` forces a store (tests use `file`).
"""
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

CHANNELS = {"x": ("auth_token", "ct0"), "reddit": ("reddit_session",)}
SERVICE = "agylite-research"
VALUE = re.compile(r"^[A-Za-z0-9%._:=+/-]{8,4096}$")   # cookie values: no spaces, quotes or newlines


class SecretError(RuntimeError):
    pass


def secrets_dir(home: Path) -> Path:
    return Path(home) / "secrets"


def _meta_path(home):
    return secrets_dir(home) / "research.json"


def _env_path(home):
    return secrets_dir(home) / "research.env"


def backend() -> str:
    forced = os.environ.get("AGYLITE_SECRETS_BACKEND")
    if forced in ("file", "keychain"):
        return forced
    return "keychain" if sys.platform == "darwin" and shutil.which("security") else "file"


def _ensure_dir(home):
    d = secrets_dir(home)
    d.mkdir(parents=True, exist_ok=True)
    os.chmod(d, 0o700)
    return d


def _meta(home) -> dict:
    p = _meta_path(home)
    return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else {}


def _write_private(path: Path, text: str):
    """Mode 0600 from creation (no window where the file is readable by others), then an atomic rename."""
    path.parent.mkdir(parents=True, exist_ok=True)
    os.chmod(path.parent, 0o700)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(text)
    os.replace(tmp, path)


def _read_env(home) -> dict:
    p = _env_path(home)
    if not p.is_file():
        return {}
    out = {}
    for line in p.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            out[k] = v
    return out


def _write_env(home, values: dict):
    _ensure_dir(home)
    body = "# Agylite research credentials (MP5 §1.2). Mode 0600. Never commit or share.\n"
    body += "".join(f"{k}={v}\n" for k, v in sorted(values.items()))
    _write_private(_env_path(home), body)


def _account(channel, name):
    return f"{channel}.{name}"


def _security(script: str):
    p = subprocess.run(["security", "-i"], input=script + "\nquit\n", capture_output=True, text=True)
    if p.returncode:
        raise SecretError("the macOS Keychain refused the change (security -i)")
    return p


def store(home, channel: str, values: dict) -> str:
    """Save one channel's values; returns the store used. Raises on a malformed value (never echoes it)."""
    names = CHANNELS[channel]
    if set(values) != set(names):
        raise SecretError(f"{channel} needs {', '.join(names)}")
    for name, value in values.items():
        if not VALUE.match(value or ""):
            raise SecretError(f"{name}: that does not look like a cookie value (no spaces or quotes); nothing saved")
    where = backend()
    if where == "keychain":
        _security("\n".join(f'add-generic-password -U -a "{_account(channel, n)}" -s "{SERVICE}" -w "{v}"'
                            for n, v in values.items()))
    else:
        env = _read_env(home)
        env.update({f"{channel.upper()}_{n.upper()}": v for n, v in values.items()})
        _write_env(home, env)
    meta = _meta(home)
    meta[channel] = {"enabled": True, "store": where, "names": list(names)}
    _write_private(_meta_path(home), json.dumps(meta, indent=1) + "\n")
    return where


def load(home, channel: str) -> dict:
    """{name: value} for an enabled channel ({} when disabled). Callers pass them only to one child process."""
    info = _meta(home).get(channel)
    if not info or not info.get("enabled"):
        return {}
    names = CHANNELS[channel]
    if info.get("store") == "keychain":
        out = {}
        for n in names:
            p = subprocess.run(["security", "find-generic-password", "-a", _account(channel, n), "-s", SERVICE, "-w"],
                               capture_output=True, text=True)
            if p.returncode:
                return {}
            out[n] = p.stdout.strip()
        return out
    env = _read_env(home)
    out = {n: env.get(f"{channel.upper()}_{n.upper()}") for n in names}
    return out if all(out.values()) else {}


def delete(home, channel: str) -> bool:
    meta = _meta(home)
    info = meta.pop(channel, None)
    if info and info.get("store") == "keychain":
        for n in CHANNELS[channel]:
            subprocess.run(["security", "delete-generic-password", "-a", _account(channel, n), "-s", SERVICE],
                           capture_output=True, text=True)
    env = _read_env(home)
    keys = [k for k in env if k.startswith(f"{channel.upper()}_")]
    if keys:
        for k in keys:
            env.pop(k)
        _write_env(home, env)
    if _meta_path(home).is_file():
        _write_private(_meta_path(home), json.dumps(meta, indent=1) + "\n")
    return bool(info or keys)


def status(home, channel: str) -> str:
    info = _meta(home).get(channel)
    return f"enabled ({info.get('store')})" if info and info.get("enabled") else "disabled"
