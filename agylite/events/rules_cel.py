"""Risk detection with bundled Agent Beacon rules (doc 15, D-017): a CEL-subset evaluator, the rule loader,
session-scoped correlation, and a runner for each rule's embedded tests.

Supported CEL subset (everything the 77 pinned Beacon rules use, plus a little headroom): field access `e.a.b`,
string/number/bool/null literals, `==` `!=` `<` `<=` `>` `>=`, `&&` `||` `!`, parentheses, `x in [..]`, and the
methods `matches(re)` `contains(s)` `startsWith(s)` `endsWith(s)` `size()`. Following Beacon's threat-rules spec,
a missing field path is an empty/zero value (`""`, `0`, `false` — whichever the other operand needs), never an
error. Type errors are error values: `false && error` is false, `true || error` is true (CEL commutative
semantics), and a condition that ends in an error does not match. RE2 patterns are mapped to Python `re` (global
`(?i)` anywhere → IGNORECASE, `\\x{HHHH}` → the code point). The derived field `e.gen_ai.tool.call.result_text` is
computed before evaluation exactly as the spec's reference derivation (`threatrules.ToolResultText`).
"""
import operator
import re
from datetime import datetime
from functools import lru_cache
from pathlib import Path

import yaml

_TOKEN = re.compile(r"""\s*(?:
    (?P<num>\d+\.\d+|\d+)|
    (?P<str>"(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*')|
    (?P<op>&&|\|\||==|!=|<=|>=|[<>!().,\[\]])|
    (?P<id>[A-Za-z_][A-Za-z0-9_]*)
)""", re.X)
_ESCAPES = {"n": "\n", "t": "\t", "r": "\r", "\\": "\\", '"': '"', "'": "'"}
_CMP = {"==": operator.eq, "!=": operator.ne, "<": operator.lt, "<=": operator.le, ">": operator.gt,
        ">=": operator.ge, "in": lambda a, b: a in b}


class CelError(ValueError):
    pass


class _Err:
    """CEL error value (type mismatch, unsupported call)."""
    def __init__(self, why):
        self.why = why


class _Missing:
    """An absent field path: behaves as the zero value of whatever it is compared with."""


MISSING = _Missing()


def _zero_like(other):
    if isinstance(other, bool):
        return False
    if isinstance(other, (int, float)):
        return 0
    if isinstance(other, list):
        return []
    return ""


def _unquote(s):
    body, out, i = s[1:-1], [], 0
    while i < len(body):
        c = body[i]
        if c == "\\" and i + 1 < len(body):
            nxt = body[i + 1]
            out.append(_ESCAPES.get(nxt, "\\" + nxt))   # unknown escapes (\d, \s, \b…) stay for the regex
            i += 2
        else:
            out.append(c)
            i += 1
    return "".join(out)


def _tokenize(src):
    pos, out = 0, []
    src = src.strip()
    while pos < len(src):
        m = _TOKEN.match(src, pos)
        if not m or m.end() == pos:
            raise CelError(f"unexpected input at {pos}: {src[pos:pos + 20]!r}")
        pos = m.end()
        kind = m.lastgroup
        val = m.group(kind)
        if kind == "num":
            out.append(("lit", float(val) if "." in val else int(val)))
        elif kind == "str":
            out.append(("lit", _unquote(val)))
        elif kind == "id" and val in ("true", "false", "null"):
            out.append(("lit", {"true": True, "false": False, "null": None}[val]))
        elif kind == "id" and val == "in":
            out.append(("op", "in"))
        else:
            out.append((kind, val))
    return out


class _Parser:
    """Precedence: || < && < ! < comparison/in < member/call < primary."""

    def __init__(self, tokens):
        self.t, self.i = tokens, 0

    def peek(self):
        return self.t[self.i] if self.i < len(self.t) else (None, None)

    def at(self, val):
        tok = self.peek()
        return tok[0] == "op" and tok[1] == val

    def take(self, val=None):
        tok = self.peek()
        if val is not None and not (tok[0] == "op" and tok[1] == val):
            raise CelError(f"expected {val!r}, got {tok[1]!r}")
        if tok[0] is None:
            raise CelError("unexpected end of expression")
        self.i += 1
        return tok

    def parse(self):
        node = self.or_()
        if self.i != len(self.t):
            raise CelError(f"trailing input {self.t[self.i:]}")
        return node

    def or_(self):
        node = self.and_()
        while self.at("||"):
            self.take()
            node = ("or", node, self.and_())
        return node

    def and_(self):
        node = self.not_()
        while self.at("&&"):
            self.take()
            node = ("and", node, self.not_())
        return node

    def not_(self):
        if self.at("!"):
            self.take()
            return ("not", self.not_())
        return self.cmp()

    def cmp(self):
        node = self.member()
        tok = self.peek()
        if tok[0] == "op" and tok[1] in _CMP:
            self.take()
            node = ("cmp", tok[1], node, self.member())
        return node

    def member(self):
        node = self.primary()
        while self.at("."):
            self.take()
            kind, name = self.take()
            if kind != "id":
                raise CelError(f"expected a field or method name after '.', got {name!r}")
            if self.at("("):
                self.take()
                args = []
                if not self.at(")"):
                    args.append(self.or_())
                    while self.at(","):
                        self.take()
                        args.append(self.or_())
                self.take(")")
                node = ("call", name, node, args)
            else:
                node = ("field", node, name)
        return node

    def primary(self):
        kind, val = self.take()
        if kind == "lit":
            return ("lit", val)
        if kind == "id":
            if self.at("("):   # global function: size(x)
                self.take()
                arg = self.or_()
                self.take(")")
                return ("call", val, arg, [])
            return ("var", val)
        if val == "(":
            node = self.or_()
            self.take(")")
            return node
        if val == "[":
            items = []
            if not self.at("]"):
                items.append(self.or_())
                while self.at(","):
                    self.take()
                    items.append(self.or_())
            self.take("]")
            return ("list", items)
        raise CelError(f"unexpected token {val!r}")


@lru_cache(maxsize=4096)
def compile_expr(src: str):
    return _Parser(_tokenize(src)).parse()


@lru_cache(maxsize=4096)
def _regex(pattern: str):
    flags = 0
    if "(?i)" in pattern:
        pattern, flags = pattern.replace("(?i)", ""), re.I
    pattern = re.sub(r"\\x\{([0-9A-Fa-f]{1,8})\}", lambda m: f"\\U{int(m.group(1), 16):08X}", pattern)
    return re.compile(pattern.replace(r"\z", r"\Z"), flags)


def _ev(node, env):
    kind = node[0]
    if kind == "lit":
        return node[1]
    if kind == "var":
        return env.get(node[1], _Err(f"unknown variable {node[1]}"))
    if kind == "list":
        return [_ev(n, env) for n in node[1]]
    if kind == "field":
        base = _ev(node[1], env)
        if isinstance(base, dict):
            value = base.get(node[2], MISSING)
            return MISSING if value is None else value
        return MISSING if isinstance(base, _Missing) else _Err(f"field {node[2]} of a non-object")
    if kind in ("and", "or"):
        short = kind == "or"            # value that decides the result on its own
        left = _ev(node[1], env)
        left = False if isinstance(left, _Missing) else left
        if left is short:
            return short
        right = _ev(node[2], env)
        right = False if isinstance(right, _Missing) else right
        if right is short:
            return short
        for v in (left, right):
            if isinstance(v, _Err):
                return v
            if not isinstance(v, bool):
                return _Err(f"{kind} on non-bool")
        return not short
    if kind == "not":
        v = _ev(node[1], env)
        v = False if isinstance(v, _Missing) else v
        return (not v) if isinstance(v, bool) else _Err("! on non-bool")
    if kind == "cmp":
        op, a, b = node[1], _ev(node[2], env), _ev(node[3], env)
        for v in (a, b):
            if isinstance(v, _Err):
                return v
        if isinstance(a, _Missing):
            a = _zero_like(b) if op != "in" else ""
        if isinstance(b, _Missing):
            b = _zero_like(a) if op != "in" else []
        try:
            return _CMP[op](a, b)
        except TypeError:
            return _Err(f"cannot compare {type(a).__name__} {op} {type(b).__name__}")
    if kind == "call":
        name, target = node[1], _ev(node[2], env)
        args = [_ev(a, env) for a in node[3]]
        target = "" if isinstance(target, _Missing) else target
        args = ["" if isinstance(a, _Missing) else a for a in args]
        for v in [target, *args]:
            if isinstance(v, _Err):
                return v
        if name == "size":
            return len(target) if isinstance(target, (str, list, dict)) else _Err("size of non-collection")
        if not isinstance(target, str) or len(args) != 1 or not isinstance(args[0], str):
            return _Err(f"{name} needs a string receiver and one string argument")
        if name == "matches":
            return bool(_regex(args[0]).search(target))
        if name == "contains":
            return args[0] in target
        if name == "startsWith":
            return target.startswith(args[0])
        if name == "endsWith":
            return target.endswith(args[0])
        return _Err(f"unsupported function {name}")
    raise CelError(f"unknown node {kind}")


RESULT_TEXT_LIMIT = 4096
_READ_TOOLS = {"webfetch", "websearch", "fetch", "fetchurl", "readurl"}


CONTENT_BLOCK_TYPES = {"text", "image", "audio", "document", "resource", "resource_link"}


def _skip_block_field(key, value) -> bool:
    """Port of Beacon `skipContentBlockField` (upstream 2462839): metadata and encoded bytes of a content block are not
    text the model reads, and base64 media would otherwise use up the result_text cap before a text block after it."""
    if key in ("type", "mimeType", "annotations", "_meta", "sha256"):
        return True
    if key in ("data", "blob"):
        return isinstance(value, str)
    return key == "source" and isinstance(value, dict) and value.get("type") == "base64"


def _collect_map(m, skip, out):
    for key in sorted(m):
        value = m[key]
        if skip and skip(key, value):
            continue
        if skip and key == "resource" and isinstance(value, dict):
            _collect_map(value, skip, out)
            continue
        _collect_strings(value, out)


def _collect_strings(value, out):
    """Port of Beacon `collectToolResultStrings`: strings in sorted key order; list elements that are content blocks
    contribute their text without metadata or encoded bytes."""
    if isinstance(value, str):
        if value.strip():
            out.append(value)
    elif isinstance(value, dict):
        _collect_map(value, None, out)
    elif isinstance(value, list):
        for item in value:
            if isinstance(item, dict) and item.get("type") in CONTENT_BLOCK_TYPES:
                _collect_map(item, _skip_block_field, out)
            else:
                _collect_strings(item, out)


def _ingested_target(path) -> bool:
    """Port of Beacon `IngestedContentTarget`: a tool whose target is an http(s) URL brought outside content in."""
    from urllib.parse import urlparse
    if not isinstance(path, str):
        return False
    parsed = urlparse(path.strip())
    return bool(parsed.netloc) and parsed.scheme.lower() in ("http", "https")


def tool_result_text(event: dict) -> str:
    """Port of Beacon `threatrules.ToolResultText`: text of a read-type tool result, capped and redacted."""
    from .redact import redact_text
    call = ((((event.get("gen_ai") or {}).get("tool") or {}).get("call")) or {})
    result = call.get("result")
    if result is None:
        return ""
    action = (event.get("event") or {}).get("action")
    mcp = event.get("mcp") or {}
    names = [n for n in ((event.get("tool") or {}).get("name"), ((event.get("gen_ai") or {}).get("tool") or {}).get("name"))
             if n]
    ingested = (action in ("file.read", "mcp.tool_invoked") or bool(mcp.get("server") or mcp.get("tool"))
                or _ingested_target((event.get("tool") or {}).get("path"))
                or any(n.strip().lower().startswith(("mcp__", "mcp:")) or
                       n.strip().lower().replace("_", "").replace("-", "") in _READ_TOOLS for n in names))
    content = event.get("content")
    retained = content is None or (content.get("included") and content.get("retention") != "metadata")
    if not (ingested and retained):
        return ""
    parts = []
    _collect_strings(result, parts)
    text = "\n".join(parts).strip()
    return redact_text(text.encode("utf-8")[:RESULT_TEXT_LIMIT].decode("utf-8", "ignore")) if text else ""


def with_derived_fields(event: dict) -> dict:
    """A copy of `event` with `gen_ai.tool.call.result_text` derived (any asserted value is replaced)."""
    call = ((((event.get("gen_ai") or {}).get("tool") or {}).get("call")) or None)
    text = tool_result_text(event)
    if not text and not (call and "result_text" in call):
        return event
    gen_ai = dict(event.get("gen_ai") or {})
    tool = dict(gen_ai.get("tool") or {})
    call = dict(tool.get("call") or {})
    call["result_text"] = text
    tool["call"], gen_ai["tool"] = call, tool
    return {**event, "gen_ai": gen_ai}


def evaluate(expr: str, event: dict) -> bool:
    """True only when the condition evaluates to boolean true for `e = event` (derived fields filled in)."""
    return _ev(compile_expr(" ".join(expr.split())), {"e": with_derived_fields(event)}) is True


# ── rules ───────────────────────────────────────────────────────────────────────────────────────────────────────
def load_rules(rules_dir: Path):
    rules = []
    for path in sorted(Path(rules_dir).rglob("*.rule.yaml")):
        with open(path, encoding="utf-8") as f:
            rule = yaml.safe_load(f)
        rule["_path"] = str(path)
        rules.append(rule)
    return rules


def rules_dir_for(bundle_dir: Path | None, staging: Path | None = None):
    """Bundled Beacon rules (`<bundle>/files/beacon/rules`), else a staged checkout (development only)."""
    for candidate in ((bundle_dir / "files" / "beacon" / "rules") if bundle_dir else None,
                      (staging / "beacon" / "rules") if staging else None):
        if candidate is not None and candidate.is_dir():
            return candidate
    return None


def _ts(event, fallback):
    raw = event.get("timestamp")
    if not raw:
        return float(fallback)
    return datetime.fromisoformat(str(raw).replace("Z", "+00:00")).timestamp()


def _window(spec) -> float:
    m = re.fullmatch(r"(\d+)\s*([smh]?)", str(spec or "0").strip())
    if not m:
        raise CelError(f"bad correlation window {spec!r}")
    return int(m.group(1)) * {"": 1, "s": 1, "m": 60, "h": 3600}[m.group(2)]


def match_rule(rule, events):
    """True when the rule fires on this event sequence (single-event rules: any event matches)."""
    if "match" in rule:
        return any(evaluate(rule["match"], e) for e in events)
    corr = rule["correlation"]
    window = _window(corr.get("window"))
    by_session = {}
    for i, e in enumerate(events):
        sid = (e.get("session") or {}).get("id") if corr.get("scope", "session") == "session" else "*"
        by_session.setdefault(sid, []).append((_ts(e, i), i, e))
    for seq in by_session.values():
        hits = [[(t, i) for t, i, e in seq if evaluate(step["match"], e)] for step in corr["steps"]]
        if any(not h for h in hits):
            continue
        if corr.get("order") == "any":
            for t0, _ in hits[0]:
                if all(any(abs(t - t0) <= window for t, _ in h) for h in hits[1:]):
                    return True
            continue

        def chain(k, prev, start_t):
            if k == len(hits):
                return True
            return any(hit > prev and hit[0] - start_t <= window and chain(k + 1, hit, start_t) for hit in hits[k])
        if any(chain(1, first, first[0]) for first in hits[0]):
            return True
    return False


def run_embedded_tests(rule):
    """[(test name, expected verdict, passed)] for one rule's `tests:` block."""
    out = []
    for t in rule.get("tests") or []:
        fired = match_rule(rule, t.get("events") or [])
        expected = t.get("verdict")
        out.append((t.get("name"), expected, fired == (expected == "match")))
    return out


def detect(rules, events):
    """Rules that fire on `events`: [{id, title, severity, reason}]."""
    found = []
    for rule in rules:
        try:
            fired = match_rule(rule, events)
        except CelError:
            continue
        if fired:
            found.append({"id": rule["id"], "title": rule.get("title"), "severity": rule.get("severity", "medium"),
                          "reason": (rule.get("emit") or {}).get("reason")})
    return found
