"""Run selected checks locally and turn their output into results (P15, D-035): exit code + parsed counts + a short
diagnosis from the failing output. A missing tool is BLOCKED (not FAILED); nothing here can start a browser, except
the one capability-scoped gate config/verification.yaml allows: `agylite diagram check|browser-check` (Archify's own
headless Chrome check of a delivered diagram, MP5 §3.3, owner approval 2026-10-22)."""
import re
import subprocess
import time

from .detect import E2E_MARKERS

DEFAULT_TIMEOUT = 900
_PYTEST = re.compile(r"(\d+) (passed|failed|skipped|errors?|xfailed|xpassed)")
_UNITTEST_RAN = re.compile(r"^Ran (\d+) tests? in", re.M)
_UNITTEST_TAIL = re.compile(r"^(OK|FAILED)(?: \((.*)\))?\s*$", re.M)
_JEST = re.compile(r"Tests:\s+(.*?)(\d+) total")
_GO = re.compile(r"^(ok|FAIL|---\s+FAIL)\b", re.M)
_DIAG = re.compile(r"(Error|FAIL|Failed|failed|assert|Traceback|error\b|✕|panic:)")
MISSING = re.compile(r"No module named ([\w.]+)|command not found|not found on PATH|ENOENT|"
                     r"is not recognized as an internal or external command")


def counts(output: str) -> dict:
    c = {}
    ran = _UNITTEST_RAN.search(output)
    if ran:
        total = int(ran.group(1))
        tail = _UNITTEST_TAIL.findall(output)
        detail = dict(kv.split("=") for kv in (tail[-1][1].split(", ") if tail and tail[-1][1] else []) if "=" in kv)
        failed = int(detail.get("failures", 0)) + int(detail.get("errors", 0))
        skipped = int(detail.get("skipped", 0))
        return {"passed": total - failed - skipped, "failed": failed, "skipped": skipped}
    m = _JEST.search(output)
    if m:
        parts = dict((k, int(v)) for v, k in re.findall(r"(\d+) (failed|passed|skipped)", m.group(1)))
        return {"passed": parts.get("passed", 0), "failed": parts.get("failed", 0), "skipped": parts.get("skipped", 0)}
    found = _PYTEST.findall(output.splitlines()[-1] if output.strip() else "")
    if found:
        for n, k in found:
            k = "failed" if k.startswith("error") else k
            c[k] = c.get(k, 0) + int(n)
        return {"passed": c.get("passed", 0), "failed": c.get("failed", 0), "skipped": c.get("skipped", 0)}
    go = _GO.findall(output)
    if go:
        return {"packages_ok": go.count("ok"), "packages_failed": len(go) - go.count("ok")}
    return c


def diagnose(output: str, limit=12) -> list:
    lines = [l.rstrip() for l in output.splitlines() if _DIAG.search(l)]
    return lines[:limit]


SCOPED_GATES = (("diagram", "check"), ("diagram", "browser-check"))


def scoped_gate(command) -> bool:
    """`… -m agylite.cli diagram [--project p] check|browser-check …`: the scoped browser gate (config/verification.yaml)."""
    args = list(command)
    if "agylite.cli" not in args:
        return False
    rest = args[args.index("agylite.cli") + 1:]
    if rest[:1] == ["diagram"] and rest[1:2] == ["--project"]:
        rest = rest[:1] + rest[3:]
    return tuple(rest[:2]) in SCOPED_GATES


def run_check(command, cwd, timeout=DEFAULT_TIMEOUT) -> dict:
    if not scoped_gate(command) and any(m in " ".join(command).lower() for m in ("chrome", "screenshot")):
        raise ValueError("browser/screenshot commands are not verification (config/verification.yaml)")
    start = time.perf_counter()
    try:
        p = subprocess.run(command, cwd=cwd, capture_output=True, text=True, timeout=timeout)
        out, code = (p.stdout or "") + (p.stderr or ""), p.returncode
    except FileNotFoundError as exc:
        out, code = f"{command[0]}: not found on PATH ({exc})", 127
    except subprocess.TimeoutExpired:
        out, code = f"timed out after {timeout}s", 124
    ms = round((time.perf_counter() - start) * 1000)
    blocked = code != 0 and (code in (127,) or (MISSING.search(out) and not counts(out)))
    result = "PASSED" if code == 0 else "BLOCKED" if blocked else "FAILED"
    return {"command": command, "exit_code": code, "result": result, "duration_ms": ms, **counts(out),
            "diagnosis": diagnose(out) if result != "PASSED" else [], "output_tail": out[-2000:]}


def is_e2e(command) -> bool:
    low = " ".join(command).lower()
    return any(m in low for m in E2E_MARKERS)
