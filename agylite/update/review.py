"""Upstream update review (MP6, owner decision 2026-10-21): know about new upstream commits, show what each changes,
judge whether it matters to Agylite, say how to adopt it safely, and switch only after the owner approves.

review:  per upstream with new commits — collect (blobless mirror, non-merge commits pin..target) → classify every
         commit by deterministic rules (no model call) → section-level diffs of the files agents read → build and check
         a candidate bundle WITHOUT activating it → Tier 0 on the candidate vs the current bundle → a verdict with
         reasons → proposed rule/rewrite edits (never applied) → `REPORT.md` + `report.json` in
         `~/.agylite/updates/review-<date>/`. The candidate is recorded in `updates/pending.json`.
approve: activate a reviewed candidate only if its checks passed and the base pins are still the current ones.
reject:  remember `{repo, sha range, reason}`; the next review classifies only the commits after that range.
"""
import difflib
import fnmatch
import json
import os
import re
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import yaml

from ..bundle.checks import MCP_FILE
from ..bundle.rules import BUNDLED, classify, compile_rules, evidence_dir, load_capabilities, load_rules, read_inventory
from ..context.sections import split_sections
from ..paths import repo_root
from .core import UpdateError, _current_evidence, _pins, switch, update

CLASS_ORDER = ("SECURITY", "POLICY", "BREAKING", "NEW_UNCLASSIFIED", "NEW_SKILL", "PRIMARY", "BUNDLED", "IRRELEVANT")
SECURITY_RX = re.compile(r"security|secret|redact|credential|token|cve|vuln|inject|sanitiz|xss|csrf|ssrf|traversal", re.I)
CONVENTIONAL = re.compile(r"^(feat|fix|refactor|docs|test|chore|ci|perf|build)(\([^)]*\))?!?:", re.I)
HOOK_FILE = re.compile(r"(^|/)(hooks/hooks\.json|hooks\.json|\.claude/settings[^/]*\.json)$", re.I)
INSTALLER = re.compile(r"(^|/)(install(er)?|setup)(\.[a-z]+)?$", re.I)
TELEMETRY = re.compile(r"posthog|telemetry|mixpanel|segment\.(io|com)|sentry\.io|amplitude|plausible|gtag\(", re.I)
LICENSE_NAME = re.compile(r"^(LICEN[CS]E|COPYING|NOTICE|THIRD[_-]PARTY)", re.I)
CODE_EXT = (".py", ".js", ".mjs", ".cjs", ".ts", ".tsx", ".sh", ".json", ".jsonc", ".yaml", ".yml", ".toml", ".go")
VERDICT_ORDER = ("SECURITY_FAST_TRACK", "ADOPT", "ADOPT_AFTER_TIER1", "NEEDS_RULES", "HOLD", "SKIP")
DIFF_LINES = 200
# MP6 §1.4: which Tier 1 suites measure a capability (the suites that exist, IMPLEMENTATION_PLAN §5).
SUITES = {"engineering/review": ["eng-ponytail"], "engineering/simplicity": ["eng-ponytail"],
          "engineering/planning": ["eng-pocock", "eng-addy"], "testing/strategy": ["eng-pocock", "eng-addy"],
          "engineering/debugging": ["eng-pocock", "eng-addy"], "engineering/implementation": ["eng-addy"],
          "engineering/diagrams": ["diagram-archify"], "design/inspiration-extract": ["design-extract"]}
SUITE_PREFIX = {"design/": ["design-taste"], "youtube/": ["youtube"], "research/": ["research"]}
RUNTIME_REPOS = {"graphify", "designlang", "archify", "agentreach", "ytagent", "taste", "unlazy", "uiuxpromax",
                 "beyondseo", "brag"}


def _now():
    return datetime.now(timezone.utc)


def _git(*args, cwd, check=True, timeout=600):
    p = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, timeout=timeout)
    if check and p.returncode:
        raise UpdateError(f"git {' '.join(args[:2])} failed: {(p.stderr or p.stdout).strip()[-300:]}")
    return p.stdout


def show(mirror: Path, sha: str, path: str):
    """A file's text at a commit (a blobless mirror fetches just that blob), or None if it does not exist."""
    p = subprocess.run(["git", "show", f"{sha}:{path}"], cwd=mirror, capture_output=True, timeout=300)
    return p.stdout.decode("utf-8", errors="replace") if p.returncode == 0 else None


# ── state files ────────────────────────────────────────────────────────────────────────────────────────────────
def _updates(home) -> Path:
    d = Path(home) / "updates"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _load(path: Path, default):
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else default


def _save(path: Path, data):
    from ..isolation import atomic
    atomic.write_text(path, json.dumps(data, indent=1, sort_keys=True) + "\n")


def pending(home) -> list:
    """Reviewed candidates that are neither approved nor rejected (local file only: no network)."""
    return [e for e in _load(_updates(home) / "pending.json", []) if e.get("state") == "pending"]


def pending_line(home) -> str | None:
    """The L0 state line (MP6 §2): read only local files, never the network."""
    try:
        n = len([e for e in pending(home) if e.get("approvable")])
    except (OSError, ValueError):
        return None
    return f"updates: {n} reviewed upstream update(s) awaiting approval (agylite update --pending)" if n else None


def rejections(home) -> list:
    return _load(_updates(home) / "rejections.json", [])


# ── classification ─────────────────────────────────────────────────────────────────────────────────────────────
def primary_paths(priorities: dict, repo: str) -> dict:
    """{bundle-path glob: capability} for the first and second `sources_priority` entries of this upstream."""
    out = {}
    for cid, globs in priorities.items():
        for g in (globs or [])[:2]:
            if g.startswith(f"files/{repo}/"):
                out[g] = cid
    return out


def _primary_cap(path, repo, prim):
    dest = f"files/{repo}/{path}"
    return next((cid for g, cid in prim.items() if fnmatch.fnmatchcase(dest, g)), None)


def _new_policy_content(path, text_of, old_text_of):
    """MCP config or telemetry that this change introduces into a code/config file (not prose that mentions it)."""
    if text_of is None or not path.lower().endswith(CODE_EXT):
        return False
    new, old = text_of(path) or "", (old_text_of(path) if old_text_of else "") or ""
    for rx in (re.compile("mcpServers"), TELEMETRY):
        if len(rx.findall(new)) > len(rx.findall(old)):
            return True
    return False


def classify_commit(commit: dict, rr: dict, *, repo: str, prim: dict, rewrite_paths: set, license_files: set,
                    text_of=None, old_text_of=None) -> dict:
    """Classes of one commit from its changed files (status A/M/D/R) — deterministic, no model call. POLICY counts only
    what would reach the bundle — an MCP/hook file or a new installer that a rule bundles, MCP config or telemetry newly
    added to a bundled code/config file, a changed license/notice file — plus any newly added MCP config file."""
    classes, primary_caps = set(), set()
    touched_bundled = touched_runtime = False
    for f in commit["files"]:
        status, path, old = f["status"], f["path"], f.get("old")
        rule, old_rule = classify(rr, path), classify(rr, old) if old else None
        bundled = rule["decision"] in BUNDLED
        old_bundled = old_rule is not None and old_rule["decision"] in BUNDLED
        touched_bundled |= bundled or old_bundled
        touched_runtime |= rule["decision"] == "EXCLUDE" and rule.get("reason") == "PRODUCT_RUNTIME"
        if status == "D" and bundled:
            classes.add("BREAKING")
        if status == "R" and old_bundled:
            classes.add("BREAKING")
        if status in ("M", "R") and (path in rewrite_paths or old in rewrite_paths):
            classes.add("BREAKING" if f.get("rewrite_drift") else "PRIMARY" if _primary_cap(path, repo, prim) else "BUNDLED")
        if status in ("M", "A", "R") and bundled:
            cap = _primary_cap(path, repo, prim)
            if cap and status != "A":
                classes.add("PRIMARY")
                primary_caps.add(cap)
            else:
                classes.add("BUNDLED")
        is_default = rule is rr["default"]
        if status == "A" and is_default:
            if path.rsplit("/", 1)[-1] == "SKILL.md":
                classes.add("NEW_SKILL")
            elif rr["default"]["decision"] != "EXCLUDE":
                classes.add("NEW_UNCLASSIFIED")
        if status in ("A", "M", "R") and bundled:
            if (MCP_FILE.search(path) or HOOK_FILE.search(path) or (INSTALLER.search(path) and status == "A")
                    or _new_policy_content(path, text_of, old_text_of)):
                classes.add("POLICY")
        if status == "A" and MCP_FILE.search(path):   # a new MCP config anywhere is held (MP6 §8)
            classes.add("POLICY")
        if path in license_files or (LICENSE_NAME.match(path.rsplit("/", 1)[-1]) and status != "A" and bundled):
            classes.add("POLICY")
    if SECURITY_RX.search(commit["subject"] + "\n" + commit.get("body", "")) and (touched_bundled or touched_runtime):
        classes.add("SECURITY")
    if not classes:
        classes.add("IRRELEVANT")
    m = CONVENTIONAL.match(commit["subject"])
    return {**commit, "classes": [c for c in CLASS_ORDER if c in classes],
            "type": m.group(1).lower() if m else "other", "primary_capabilities": sorted(primary_caps)}


def collect(mirror: Path, base: str, target: str, skip_until: str | None = None) -> list:
    """Non-merge commits base..target, oldest first, with each file's status (renames detected)."""
    spec = [f"{skip_until}..{target}"] if skip_until else [f"{base}..{target}"]
    shas = _git("rev-list", "--no-merges", "--reverse", *spec, cwd=mirror).split()
    out = []
    for sha in shas:
        meta = _git("show", "-s", "--format=%H%x00%aI%x00%an%x00%s%x00%b", sha, cwd=mirror).split("\x00")
        files = []
        for line in _git("diff-tree", "--no-commit-id", "-r", "-M", "--name-status", sha, cwd=mirror).splitlines():
            parts = line.split("\t")
            st = parts[0][0]
            if st == "R":
                files.append({"status": "R", "old": parts[1], "path": parts[2]})
            elif st in "AMDT":
                files.append({"status": "M" if st == "T" else st, "path": parts[1]})
        out.append({"sha": meta[0], "date": meta[1], "author": meta[2], "subject": meta[3],
                    "body": (meta[4] if len(meta) > 4 else "").strip()[:2000], "files": files})
    return out


def net_changes(mirror: Path, base: str, target: str) -> list:
    """Each path's net change base→target (A/M/D/R)."""
    rows = []
    for line in _git("diff", "--name-status", "-M", base, target, cwd=mirror).splitlines():
        parts = line.split("\t")
        st = parts[0][0]
        rows.append({"status": "R", "old": parts[1], "path": parts[2]} if st == "R" else
                    {"status": "M" if st == "T" else st, "path": parts[1]})
    return rows


# ── section diffs ──────────────────────────────────────────────────────────────────────────────────────────────
def _sections(text):
    secs = split_sections(text or "")
    return {s.id: (s.title, text[s.start:s.end], s.tokens) for s in secs}


def section_diff(old: str | None, new: str | None, *, full=False) -> dict:
    """Added, removed and changed `#`–`###` sections with token deltas; the unified diff of the changed ones (full)."""
    a, b = _sections(old), _sections(new)
    added = [{"id": k, "title": b[k][0], "tokens": b[k][2]} for k in b if k not in a]
    removed = [{"id": k, "title": a[k][0], "tokens": -a[k][2]} for k in a if k not in b]
    changed = [{"id": k, "title": b[k][0], "tokens": b[k][2] - a[k][2]} for k in b if k in a and a[k][1] != b[k][1]]
    out = {"added": added, "removed": removed, "changed": changed,
           "token_delta": sum(x["tokens"] for x in added + removed + changed)}
    if full:
        lines = []
        for c in changed:
            lines += list(difflib.unified_diff(a[c["id"]][1].splitlines(), b[c["id"]][1].splitlines(),
                                               f"a §{c['id']}", f"b §{c['id']}", lineterm="", n=2))
        for x in added:
            lines += [f"+++ new §{x['id']}"] + ["+" + l for l in b[x["id"]][1].splitlines()]
        for x in removed:
            lines += [f"--- removed §{x['id']}"] + ["-" + l for l in a[x["id"]][1].splitlines()]
        out["diff"] = lines
    return out


# ── runtime upstreams ──────────────────────────────────────────────────────────────────────────────────────────
VERSION_FILES = ("package.json", "pyproject.toml", "archify/package.json", "archify/skill-release.json")


def _version(text, name):
    if not text:
        return None
    if name.endswith(".json"):
        try:
            return json.loads(text).get("version")
        except ValueError:
            return None
    m = re.search(r'^version\s*=\s*"([^"]+)"', text, re.M)
    return m.group(1) if m else None


def changelog_between(text: str | None, old_v: str | None, new_v: str | None) -> str:
    """The CHANGELOG.md sections after `old_v` up to and including `new_v` (versions as `## …x.y.z…` headings)."""
    if not text or not new_v or old_v == new_v:
        return ""
    heads = [(m.start(), m.group(0)) for m in re.finditer(r"^#{1,3} .*$", text, re.M)]
    out, take = [], False
    for i, (start, head) in enumerate(heads):
        end = heads[i + 1][0] if i + 1 < len(heads) else len(text)
        if new_v in head:
            take = True
        if old_v and old_v in head:
            break
        if take:
            out.append(text[start:end].rstrip())
    return "\n\n".join(out)[:6000]


# ── proposals (never applied) ──────────────────────────────────────────────────────────────────────────────────
def proposals(repo, rr, net, *, cards_bm25=None, priorities=None, bundle_index=None, read_new=None) -> list:
    """Concrete rule/rewrite edits for BREAKING and NEW_* changes, default-safe (new skills → REFERENCE)."""
    out = []
    for f in net:
        st, path, old = f["status"], f["path"], f.get("old")
        if st == "R" and classify(rr, old)["decision"] in BUNDLED:
            rule = classify(rr, old)
            new_rule = {"paths": [path], "decision": rule["decision"], "capability": rule.get("capability"),
                        "reason": f"renamed upstream from {old}"}
            prio = [f"{cid}: {g} → files/{repo}/{path}" for cid, gs in (priorities or {}).items() for g in gs or []
                    if fnmatch.fnmatchcase(f"files/{repo}/{old}", g) and not any(ch in g for ch in "*?[")]
            out.append({"kind": "rename", "old": old, "new": path, "rule": new_rule, "sources_priority": prio,
                        "blocking": False})
        elif st == "D" and classify(rr, path)["decision"] in BUNDLED:
            cap = classify(rr, path).get("capability")
            left = [p for p in (bundle_index or {}).get(cap, []) if p != f"files/{repo}/{path}"]
            out.append({"kind": "delete", "path": path, "capability": cap, "remaining_sources": len(left),
                        "blocking": not left})
        elif st == "A" and classify(rr, path) is rr["default"] and path.rsplit("/", 1)[-1] == "SKILL.md":
            text = (read_new(path) if read_new else "") or ""
            desc = " ".join(re.findall(r"^(?:name|description):\s*(.+)$", text[:2000], re.M)) or path
            top = cards_bm25.top(desc, 3, 0.0, 0.0) if cards_bm25 is not None else []
            folder = path.rsplit("/", 1)[0]
            out.append({"kind": "new_skill", "path": path, "candidates": [{"capability": c, "score": round(s, 2)}
                                                                          for c, s in top],
                        "rule": {"paths": [f"{folder}/**"], "decision": "REFERENCE",
                                 "reason": "new upstream skill; REFERENCE until the owner adopts it (MP6 §1.6)"},
                        "blocking": False})
        elif st == "A" and classify(rr, path) is rr["default"] and rr["default"]["decision"] != "EXCLUDE":
            out.append({"kind": "unclassified", "path": path,
                        "rule": {"paths": [path], "decision": "EXCLUDE", "reason": "OUT_OF_DOMAIN"}, "blocking": False})
    return out


def rule_snippet(repo, props) -> str:
    rules = [p["rule"] for p in props if p.get("rule")]
    if not rules:
        return ""
    return yaml.safe_dump({"repos": {repo: {"rules": rules}}}, sort_keys=False, width=120)


def rules_patch(rules_path: Path, repo: str, props) -> str:
    """A unified diff that inserts the proposed rules at the top of this repo's `rules:` list (first match wins)."""
    rules = [p["rule"] for p in props if p.get("rule")]
    if not rules:
        return ""
    text = Path(rules_path).read_text(encoding="utf-8")
    m = re.search(rf"^  {re.escape(repo)}:\n(?:.*\n)*?    rules:\n", text, re.M)
    if not m:
        return ""
    lines = "".join("      - " + json.dumps({k: v for k, v in r.items() if v is not None}, ensure_ascii=False)
                    .replace('"paths"', "paths").replace('"decision"', "decision").replace('"capability"', "capability")
                    .replace('"reason"', "reason") + "   # MP6 review proposal\n" for r in rules)
    new = text[: m.end()] + lines + text[m.end():]
    return "".join(difflib.unified_diff(text.splitlines(True), new.splitlines(True), "a/tools/audit/extraction-rules.yaml",
                                        "b/tools/audit/extraction-rules.yaml"))


# ── verdict ────────────────────────────────────────────────────────────────────────────────────────────────────
def verdict(counts: Counter, build_status: str | None, tier0_regression: list) -> tuple:
    """(verdict, reasons) by MP6 §1.5's rules."""
    if counts.get("POLICY"):
        return "HOLD", ["POLICY: MCP, hooks, telemetry, installer or license change in the new tree"]
    if counts.get("BREAKING") or counts.get("NEW_UNCLASSIFIED"):
        why = [f"{k}: {counts[k]} commit(s)" for k in ("BREAKING", "NEW_UNCLASSIFIED") if counts.get(k)]
        return "NEEDS_RULES", why + ["apply the proposed rules, then run --review again"]
    if build_status not in ("candidate", None):
        return "HOLD", [f"candidate build/check {build_status}"]
    if tier0_regression:
        return "HOLD", ["Tier 0 regression: " + "; ".join(tier0_regression[:3])]
    relevant = sum(v for k, v in counts.items() if k != "IRRELEVANT")
    if not relevant:
        return "SKIP", ["only commits Agylite does not load; move the pin anyway (hygiene)"]
    base = "ADOPT_AFTER_TIER1" if counts.get("PRIMARY") else "ADOPT"
    if counts.get("SECURITY"):
        return "SECURITY_FAST_TRACK", ["SECURITY commit(s) touching bundled/runtime paths"] + (
            ["a PRIMARY file changed: Tier 1 recommended"] if base == "ADOPT_AFTER_TIER1" else [])
    return base, (["a PRIMARY file changed: run the Tier 1 plan first"] if base == "ADOPT_AFTER_TIER1" else
                  ["checks and Tier 0 pass; nothing agents read by default changed"])


def suites_for(caps) -> list:
    out = []
    for cid in caps:
        names = SUITES.get(cid) or next((v for p, v in SUITE_PREFIX.items() if cid.startswith(p)), [])
        out += [n for n in names if n not in out]
    return out


def tier0_regression(cand: dict, cur: dict) -> list:
    """What got worse on the candidate bundle (routing failures, context selection, tokens, self-tests)."""
    bad = []
    before = {f["id"] for f in (cur.get("routing") or {}).get("failed", [])}
    new_fail = [f["id"] for f in (cand.get("routing") or {}).get("failed", []) if f["id"] not in before]
    if new_fail:
        bad.append("routing: " + ", ".join(new_fail[:5]))
    rows_c = {r["capability"]: r["ok"] for r in (cand.get("context_selection") or {}).get("rows", [])}
    rows_o = {r["capability"]: r["ok"] for r in (cur.get("context_selection") or {}).get("rows", [])}
    lost = [c for c, ok in rows_c.items() if not ok and rows_o.get(c, True)]
    if lost:
        bad.append("context selection: " + ", ".join(lost[:5]))
    if not (cand.get("tokens") or {}).get("ok", True) and (cur.get("tokens") or {}).get("ok", True):
        bad.append("tokens regressed")
    st_c = (cand.get("self_tests") or {}).get("results", {})
    st_o = (cur.get("self_tests") or {}).get("results", {})
    broke = [k for k, v in st_c.items() if v.get("exit") != 0 and (st_o.get(k) or {}).get("exit", 0) == 0]
    if broke:
        bad.append("self-tests: " + ", ".join(broke))
    return bad


def fidelity_deltas(cand: dict, cur: dict) -> list:
    old = {r["capability"]: r.get("tokens") for r in (cur.get("fidelity") or {}).get("rows", [])}
    return [{"capability": r["capability"], "before": old.get(r["capability"]), "after": r.get("tokens")}
            for r in (cand.get("fidelity") or {}).get("rows", []) if old.get(r["capability"]) != r.get("tokens")]


# ── the review ─────────────────────────────────────────────────────────────────────────────────────────────────
def review(home: Path, *, repos=None, only_due=False, tracks=None, to: str | None = None, out: Path | None = None,
           tier1_plan=False, policy=None, staging=None, evidence=None, rules_path=None, licenses_path=None,
           priorities=None, run_tier0=True, check_registry=True, log=print) -> dict:
    """Review every selected upstream with new commits. Never activates anything."""
    from . import track
    home = Path(home)
    policy = policy or track.load_policy()
    evidence = track._baseline(home, evidence)
    rules_path = Path(rules_path) if rules_path else repo_root() / "tools" / "audit" / "extraction-rules.yaml"
    rules_doc = load_rules(rules_path)
    compile_rules(rules_doc, load_capabilities())
    pins = _pins(evidence)
    if priorities is None:
        from ..context.levels import source_priorities
        priorities = source_priorities()
    from ..bundle.transforms.rewrites import REWRITES
    cur_bundle = (home / "bundles" / "current").resolve() if (home / "bundles" / "current").exists() else None
    bundle_index = _bundle_caps(cur_bundle)
    bm25 = _cards_bm25()
    licenses = _load(Path(licenses_path) if licenses_path else repo_root() / "third_party" / "licenses.json", {})
    state = track._state(home)
    stamp = _now()
    out = Path(out) if out else _updates(home) / f"review-{stamp.strftime('%Y-%m-%d')}"
    out.mkdir(parents=True, exist_ok=True)
    cur_tier0 = None
    results = []
    for name in sorted(repos or pins):
        pol = policy.get(name, {"track": "weekly", "branch": "main"})
        if name not in pins or name not in rules_doc["repos"]:
            results.append({"repo": name, "verdict": "HOLD", "why": ["unknown upstream"]})
            continue
        if not repos and (pol.get("track") == "manual" or (only_due and not track.due(name, pol, state))
                          or (tracks and pol.get("track") not in tracks)):
            continue
        base = pins[name]["head"]
        try:
            target = to if (to and repos and len(repos) == 1) else track.remote_latest(pins[name]["repo"], pol)
        except (subprocess.SubprocessError, UpdateError, OSError) as exc:
            results.append({"repo": name, "verdict": "HOLD", "why": [f"remote check failed: {str(exc)[-200:]}"]})
            continue
        if target == base:
            results.append({"repo": name, "upstream": pins[name]["repo"], "from": base, "to": target, "commits": 0,
                            "verdict": "UP_TO_DATE", "why": ["pin is the newest commit"]})
            _clear_pending(home, name)
            continue
        if pol.get("track") == "releases" and _is_ancestor(home, pins[name]["repo"], target, base):
            results.append({"repo": name, "upstream": pins[name]["repo"], "from": base, "to": target, "commits": 0,
                            "verdict": "UP_TO_DATE", "why": ["the pin is newer than the newest release tag"]})
            _clear_pending(home, name)
            continue
        log(f"reviewing {name} {base[:7]} → {target[:7]} …")
        try:
            r = _review_one(home, name, pins, base, target, pol, rules_doc["repos"][name], priorities, REWRITES,
                            licenses.get(name, {}), bundle_index, bm25, out, staging=staging, evidence=evidence,
                            rules_path=rules_path, licenses_path=licenses_path, check_registry=check_registry, log=log)
        except (UpdateError, subprocess.SubprocessError, OSError) as exc:
            results.append({"repo": name, "upstream": pins[name]["repo"], "from": base, "to": target,
                            "verdict": "HOLD", "why": [f"review failed: {str(exc)[-300:]}"]})
            continue
        if run_tier0 and r["build"].get("status") == "candidate":
            from ..benchmark.quality import tier0
            if cur_tier0 is None and cur_bundle is not None:
                cur_tier0 = tier0.run(bundle=cur_bundle)
            cand = tier0.run(bundle=home / "bundles" / r["build"]["bundle_id"])
            r["tier0"] = {"ok": cand["ok"], "regression": tier0_regression(cand, cur_tier0 or {}),
                          "fidelity_deltas": fidelity_deltas(cand, cur_tier0 or {}),
                          "self_tests": {k: v.get("exit") for k, v in (cand.get("self_tests") or {}).get("results", {}).items()}}
        reg = (r.get("tier0") or {}).get("regression", [])
        r["verdict"], r["why"] = verdict(Counter(c for k in r["commits"] for c in k["classes"]),
                                         r["build"].get("status"), reg)
        r["tier1_plan"] = _tier1_plan(r, home, tier1_plan)
        caps = sorted({c for k in r["commits"] for c in k.get("primary_capabilities", [])})
        r["unmeasured"] = [c for c in caps if not suites_for([c])]
        results.append(r)
        _record_pending(home, r, pins, out)
    report = {"at": stamp.isoformat(), "dir": str(out), "upstreams": results,
              "unmatched": _unmatched(home, since=_last_review(home))}
    _save(out / "report.json", report)
    (out / "REPORT.md").write_text(render(report), encoding="utf-8")
    _save(_updates(home) / "last-review.json", {"at": stamp.isoformat(), "dir": str(out)})
    for name in [r["repo"] for r in results if r.get("verdict") not in ("HOLD",) and "verdict" in r]:
        state.setdefault(name, {})["reviewed_check"] = stamp.isoformat()
    track._save_state(home, state)
    return report


def _review_one(home, name, pins, base, target, pol, rr, priorities, rewrites, lic, bundle_index, bm25, out, *,
                staging, evidence, rules_path, licenses_path, check_registry, log):
    from . import track
    mp = track.mirror(home, pins[name]["repo"])
    rej = [x for x in rejections(home) if x["repo"] == name and x.get("from") == base]
    skip_until = rej[-1]["to"] if rej else None
    rejected = int(_git("rev-list", "--no-merges", "--count", f"{base}..{skip_until}", cwd=mp).strip()) if skip_until else 0
    prim = primary_paths(priorities, name)
    rewrite_paths = {p for (r, p) in rewrites if r == name}
    lic_files = set(lic.get("license_files") or [])
    commits = collect(mp, base, target, skip_until)
    old_cache = {}

    def old_text_at(path):
        if path not in old_cache:
            old_cache[path] = show(mp, base, path)
        return old_cache[path]
    drift = _rewrite_drift(mp, name, target, rewrite_paths)
    text_cache = {}

    def text_at(path):
        if path not in text_cache:
            text_cache[path] = show(mp, target, path)
        return text_cache[path]
    for c in commits:
        for f in c["files"]:
            if f["path"] in drift:
                f["rewrite_drift"] = True
    classified = [classify_commit(c, rr, repo=name, prim=prim, rewrite_paths=rewrite_paths, license_files=lic_files,
                                  text_of=text_at, old_text_of=old_text_at) for c in commits]
    net = net_changes(mp, base, target)
    files = []
    for f in net:
        path = f["path"]
        if classify(rr, path)["decision"] not in BUNDLED or not path.lower().endswith((".md", ".mdx", ".tmpl")):
            continue
        cap = _primary_cap(path, name, prim) if f["status"] != "A" else None
        old_text = show(mp, base, f.get("old") or path) if f["status"] != "A" else None
        new_text = text_at(path) if f["status"] != "D" else None
        sd = section_diff(old_text, new_text, full=bool(cap))
        if "diff" in sd and len(sd["diff"]) > DIFF_LINES:
            dpath = out / f"{name}--{path.replace('/', '__')}.diff"
            dpath.write_text("\n".join(sd["diff"]) + "\n", encoding="utf-8")
            sd["diff"], sd["diff_file"] = sd["diff"][:DIFF_LINES], str(dpath)
        files.append({"path": path, "status": f["status"], "primary": cap, **sd})
    runtime = None
    if name in RUNTIME_REPOS:
        versions = {}
        for vf in VERSION_FILES:
            o, n = _version(show(mp, base, vf), vf), _version(show(mp, target, vf), vf)
            if o or n:
                versions[vf] = {"from": o, "to": n}
        main = next((v for v in versions.values() if v["from"] != v["to"]), None)
        cl = next((p for p in ("CHANGELOG.md", "archify/CHANGELOG.md") if show(mp, target, p)), None)
        runtime = {"versions": versions, "changelog": changelog_between(show(mp, target, cl) if cl else None,
                                                                        (main or {}).get("from"), (main or {}).get("to"))}
    props = proposals(name, rr, net, cards_bm25=bm25, priorities=priorities, bundle_index=bundle_index, read_new=text_at)
    patch = rules_patch(rules_path, name, props)
    if patch:
        (out / f"{name}-proposed-rules.patch").write_text(patch, encoding="utf-8")
        (out / f"{name}-proposed-rules.yaml").write_text(rule_snippet(name, props), encoding="utf-8")
    counts = Counter(c for k in classified for c in k["classes"])
    blocking = counts.get("POLICY") or counts.get("BREAKING") or counts.get("NEW_UNCLASSIFIED")
    build = {"status": "not-built", "reason": "classification needs rule changes or a policy decision first"}
    if not blocking:
        rep = update(home, name, target, mirror_path=mp, staging=staging, evidence=evidence, rules_path=rules_path,
                     licenses_path=licenses_path, self_test=bool(pol.get("self_test")), check_registry=check_registry,
                     activate=False, log=log)
        build = {k: rep.get(k) for k in ("status", "bundle_id", "errors", "warnings", "diff", "self_tests")}
    return {"repo": name, "upstream": pins[name]["repo"], "from": base, "to": target, "commits": classified,
            "rejected_commits": rejected, "counts": dict(counts), "files": files, "runtime": runtime,
            "proposals": props, "patch": bool(patch), "build": build,
            "rewrite_drift": drift}


def _is_ancestor(home, upstream, older, newer) -> bool:
    from . import track
    mp = track.mirror(home, upstream)
    return subprocess.run(["git", "merge-base", "--is-ancestor", older, newer], cwd=mp, capture_output=True).returncode == 0


def _rewrite_drift(mp, repo, target, paths) -> dict:
    """{path: the RewriteDrift message} for REWRITES entries that no longer match the new upstream text."""
    from ..bundle.transforms.rewrites import RewriteDrift, apply
    bad = {}
    for p in paths:
        text = show(mp, target, p)
        if text is None:
            continue
        try:
            apply(repo, p, text)
        except RewriteDrift as exc:
            bad[p] = str(exc)
    return bad


def _tier1_plan(r, home, want) -> list:
    caps = sorted({c for k in r["commits"] for c in k.get("primary_capabilities", [])})
    if not caps or not r["build"].get("bundle_id"):
        return []
    from ..benchmark.quality import tier1
    plan = []
    bundle = Path(home) / "bundles" / r["build"]["bundle_id"]
    for s in suites_for(caps):
        try:
            sessions = len(tier1.plan(s, arms=("agylite",))[2]) if want else None
        except KeyError:
            continue
        plan.append({"suite": s, "sessions": sessions, "command":
                     f"agylite benchmark --quality --tier 1 --suite {s} --arms agylite --bundle {bundle} --yes-spend "
                     f"--reuse-from <the suite's last run dir>"})
    return plan


def _bundle_caps(bundle) -> dict:
    if not bundle or not (Path(bundle) / "index.json").is_file():
        return {}
    return json.loads((Path(bundle) / "index.json").read_text(encoding="utf-8")).get("capabilities", {})


def _cards_bm25():
    try:
        from ..routing import Router
        return Router().bm25
    except Exception:   # noqa: BLE001 — proposals still work without a capability suggestion
        return None


def _last_review(home):
    return (_load(_updates(home) / "last-review.json", {}) or {}).get("at")


def _unmatched(home, since=None) -> list:
    """MP6 §1.7: requests nobody routed since the last review, grouped by their content words (MP1 F4 events from
    `agylite route`). The prompt hook never stores prompt words (privacy), so its unmatched prompts are only counted."""
    groups, hook_only = Counter(), 0
    for f in Path(home).glob("projects/*/events/*.jsonl"):
        for line in f.read_text(encoding="utf-8", errors="ignore").splitlines():
            try:
                e = json.loads(line)
            except ValueError:
                continue
            if e.get("event") != "ROUTE_UNMATCHED" or (since and (e.get("ts") or e.get("at") or "") < since):
                continue
            words = tuple(sorted((e.get("details") or {}).get("keywords") or [])[:4])
            if words:
                groups[words] += 1
            else:
                hook_only += 1
    rows = [{"words": list(k), "count": n} for k, n in groups.most_common(20)]
    return rows + ([{"words": ["(prompt-hook prompts; words not stored)"], "count": hook_only}] if hook_only else [])


def _clear_pending(home, repo):
    path = _updates(home) / "pending.json"
    entries = _load(path, [])
    keep = [e for e in entries if not (e["repo"] == repo and e.get("state") == "pending")]
    if len(keep) != len(entries):
        _save(path, keep)


def _record_pending(home, r, pins, out):
    entries = _load(_updates(home) / "pending.json", [])
    entries = [e for e in entries if not (e["repo"] == r["repo"] and e.get("state") == "pending")]
    entries.append({"repo": r["repo"], "from": r["from"], "sha": r["to"], "bundle_id": r["build"].get("bundle_id"),
                    "verdict": r["verdict"], "build": r["build"].get("status"), "review": str(out),
                    "base_pins": {n: p["head"] for n, p in pins.items()}, "at": _now().isoformat(), "state": "pending",
                    "approvable": r["build"].get("status") == "candidate" and r["verdict"] not in ("HOLD", "NEEDS_RULES"),
                    "tree": str(Path(home) / "updates" / f"{r['repo']}-{r['to'][:12]}" / "staging" / r["repo"])})
    _save(_updates(home) / "pending.json", entries)


# ── approve / reject ───────────────────────────────────────────────────────────────────────────────────────────
def _who():
    p = subprocess.run(["git", "config", "user.name"], capture_output=True, text=True)
    return p.stdout.strip() or os.environ.get("USER") or "owner"


def approve(home: Path, repo: str, sha: str | None = None, review_dir: str | None = None, evidence=None) -> dict:
    """Activate a reviewed candidate. Refuses unreviewed, failed or stale candidates."""
    from . import track
    home = Path(home)
    entries = _load(_updates(home) / "pending.json", [])
    match = [e for e in entries if e["repo"] == repo and e.get("state") == "pending"
             and (not sha or e["sha"].startswith(sha)) and (not review_dir or e["review"] == str(review_dir))]
    if not match:
        raise UpdateError(f"no reviewed candidate for {repo}{'@' + sha if sha else ''}; run `agylite update --review "
                          f"--repo {repo}` first")
    e = match[-1]
    if not e.get("approvable"):
        raise UpdateError(f"{repo}@{e['sha'][:7]} is {e['verdict']} (build {e['build']}); it cannot be approved — "
                          f"see {e['review']}/REPORT.md")
    now_pins = {n: p["head"] for n, p in _pins(track._baseline(home, evidence)).items()}
    if now_pins != e["base_pins"]:
        raise UpdateError("review is stale; run --review again")
    bundle = home / "bundles" / e["bundle_id"]
    from ..bundle import build as bundle_build
    problems = bundle_build.verify(bundle) if bundle.is_dir() else [f"bundle {e['bundle_id']} is missing"]
    if problems:
        raise UpdateError(f"candidate bundle {e['bundle_id']} is not intact: {problems[0]}")
    switch(home, repo, e["bundle_id"], Path(e["tree"]))
    e.update(state="approved", approved_by=_who(), approved_at=_now().isoformat())
    _save(_updates(home) / "pending.json", entries)
    decision = {"decision": "upstream update approved", "repo": repo, "from": e["from"], "to": e["sha"],
                "bundle_id": e["bundle_id"], "verdict": e["verdict"], "report": e["review"], "who": e["approved_by"],
                "at": e["approved_at"]}
    with open(_updates(home) / "decisions.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(decision) + "\n")
    st = track._state(home)
    st.setdefault(repo, {}).update(applied=e["sha"], applied_check=e["approved_at"])
    track._save_state(home, st)
    return {"status": "activated", **decision}


def reject(home: Path, repo: str, sha: str, reason: str) -> dict:
    entries = _load(_updates(home) / "pending.json", [])
    e = next((x for x in reversed(entries) if x["repo"] == repo and x["sha"].startswith(sha)), None)
    base = e["from"] if e else None
    if base is None:
        from . import track
        base = _pins(track._baseline(Path(home), None))[repo]["head"]
    row = {"repo": repo, "from": base, "to": e["sha"] if e else sha, "reason": reason, "at": _now().isoformat(),
           "who": _who()}
    data = rejections(home) + [row]
    _save(_updates(home) / "rejections.json", data)
    if e:
        e["state"] = "rejected"
        _save(_updates(home) / "pending.json", entries)
    return row


# ── report ─────────────────────────────────────────────────────────────────────────────────────────────────────
def _short(sha):
    return (sha or "")[:7]


def render(report: dict) -> str:
    ups = report["upstreams"]
    order = {v: i for i, v in enumerate(VERDICT_ORDER + ("UP_TO_DATE",))}
    ups = sorted(ups, key=lambda r: (order.get(r.get("verdict"), 9), r["repo"]))
    L = [f"# Upstream update review — {report['at'][:10]}", "",
         "Nothing here is active. Approve with `agylite update --approve <repo>`; reject with "
         "`agylite update --reject <repo>@<sha> --reason \"…\"`.", "",
         "| Upstream | Commits | Verdict | Why | Candidate bundle |", "|---|---:|---|---|---|"]
    for r in ups:
        n = len(r["commits"]) if isinstance(r.get("commits"), list) else r.get("commits", "—")
        L.append(f"| {r['repo']} | {n} | **{r.get('verdict')}** | {'; '.join(r.get('why') or [])} | "
                 f"{(r.get('build') or {}).get('bundle_id') or '—'} |")
    sec = [r for r in ups if r.get("verdict") == "SECURITY_FAST_TRACK"]
    L += ["", "## Security fast-track", ""]
    L += [f"- **{r['repo']}**: " + "; ".join(f"`{_short(c['sha'])}` {c['subject']}" for c in r["commits"]
                                              if "SECURITY" in c["classes"]) for r in sec] or ["- none"]
    for r in ups:
        if not isinstance(r.get("commits"), list) or r.get("verdict") in ("SKIP", "UP_TO_DATE"):
            continue
        L += ["", f"## {r['repo']} — {r['verdict']} ({_short(r['from'])} → {_short(r['to'])}, {len(r['commits'])} commits"
              + (f"; {r['rejected_commits']} previously rejected" if r.get("rejected_commits") else "") + ")", ""]
        L.append("Counts: " + ", ".join(f"{k} {v}" for k, v in sorted(r["counts"].items(), key=lambda kv: CLASS_ORDER.index(kv[0]))))
        rel = [c for c in r["commits"] if c["classes"] != ["IRRELEVANT"]]
        if rel:
            L += ["", "| Commit | Date | Type | Classes | Subject |", "|---|---|---|---|---|"]
            L += [f"| `{_short(c['sha'])}` | {c['date'][:10]} | {c['type']} | {', '.join(c['classes'])} | "
                  f"{c['subject'][:90].replace('|', '/')} |" for c in rel[:40]]
            if len(rel) > 40:
                L.append(f"| … | | | | {len(rel) - 40} more in report.json |")
        for f in r["files"]:
            if not (f["added"] or f["removed"] or f["changed"]):
                continue
            L += ["", f"### {f['path']} ({f['status']}{', PRIMARY of ' + f['primary'] if f['primary'] else ''}; "
                      f"{f['token_delta']:+} est. tokens)", ""]
            for kind in ("added", "removed", "changed"):
                if f[kind]:
                    L.append(f"- {kind}: " + ", ".join(f"§{x['id']} ({x['tokens']:+})" for x in f[kind][:12]))
            if f.get("diff"):
                L += ["", "```diff", *f["diff"], "```"]
            if f.get("diff_file"):
                L.append(f"Full diff: {f['diff_file']}")
        if r.get("runtime") and (r["runtime"]["versions"] or r["runtime"]["changelog"]):
            L += ["", "Runtime: " + ", ".join(f"{k} {v['from']} → {v['to']}" for k, v in r["runtime"]["versions"].items())]
            if r["runtime"]["changelog"]:
                L += ["", "<details><summary>Changelog</summary>", "", r["runtime"]["changelog"], "", "</details>"]
        b = r["build"]
        L += ["", f"Candidate: {b.get('status')}" + (f" `{b['bundle_id']}`" if b.get("bundle_id") else "")
              + (f" — {b.get('reason')}" if b.get("reason") else "")]
        if b.get("errors"):
            L += [f"- {e}" for e in b["errors"][:8]]
        if b.get("self_tests"):
            L.append("Self-tests: " + ", ".join(f"{k} exit {v.get('exit')}" for k, v in b["self_tests"].items()))
        if r.get("tier0"):
            t = r["tier0"]
            L.append(f"Tier 0 on the candidate: {'PASS' if t['ok'] else 'FAIL'}; regression vs current: "
                     f"{'; '.join(t['regression']) or 'none'}")
            if t["fidelity_deltas"]:
                L.append("Fidelity changes: " + ", ".join(f"{d['capability']} {d['before']} → {d['after']}"
                                                          for d in t["fidelity_deltas"][:10]))
        if r.get("unmeasured"):
            L.append("PRIMARY changes no Tier 1 suite measures yet: " + ", ".join(r["unmeasured"])
                     + " (judge the section diffs above)")
        if r.get("tier1_plan"):
            L += ["", "Tier 1 plan (not run; the owner decides the spend):"]
            L += [f"- `{p['command']}`" + (f" ({p['sessions']} sessions)" if p.get("sessions") is not None else "")
                  for p in r["tier1_plan"]]
        if r.get("proposals"):
            L += ["", "Proposed edits (not applied):"]
            for p in r["proposals"]:
                if p["kind"] == "rename":
                    L.append(f"- rename `{p['old']}` → `{p['new']}`: rule `{json.dumps(p['rule'])}`"
                             + (f"; sources_priority {', '.join(p['sources_priority'])}" if p["sources_priority"] else ""))
                elif p["kind"] == "delete":
                    L.append(f"- deleted `{p['path']}` ({p['capability']}): {p['remaining_sources']} other source(s) left"
                             + (" — **blocking: the capability would be empty**" if p["blocking"] else ""))
                elif p["kind"] == "new_skill":
                    L.append(f"- new skill `{p['path']}`: proposed REFERENCE; best capabilities "
                             + ", ".join(f"{c['capability']} ({c['score']})" for c in p["candidates"]))
                else:
                    L.append(f"- unclassified `{p['path']}`: proposed EXCLUDE")
            if r.get("patch"):
                L.append(f"Patch: `{r['repo']}-proposed-rules.patch` in this folder")
        if r.get("rewrite_drift"):
            L += ["", "Rewrite drift (update the REWRITES entry in agylite/bundle/transforms/rewrites.py, compare the "
                      "region in the upstream file):"]
            L += [f"- `{p}`: {msg}" for p, msg in sorted(dict(r["rewrite_drift"]).items())]
        if r.get("verdict") not in ("HOLD", "NEEDS_RULES"):
            L.append(f"Approve: `agylite update --approve {r['repo']}@{_short(r['to'])}`")
    L += ["", "## Irrelevant", ""]
    L += [f"- {r['repo']}: {r['counts'].get('IRRELEVANT', 0)} irrelevant commit(s)" for r in ups
          if isinstance(r.get("commits"), list) and r.get("counts", {}).get("IRRELEVANT")] or ["- none"]
    L += ["", "## Requests nobody routed (since the last review)", ""]
    L += [f"- {', '.join(g['words'])} — {g['count']}" for g in report.get("unmatched") or []] or ["- none recorded"]
    return "\n".join(L) + "\n"
