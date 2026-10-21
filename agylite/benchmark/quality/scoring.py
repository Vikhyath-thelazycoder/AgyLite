"""Retained gain and verdicts (MP2 §3.4, IMPLEMENTATION_PLAN §5).

retained = (agylite − baseline) ÷ (upstream − baseline) per metric, sign flipped when lower is better.
same ≥ 0.90 · near 0.70–0.90 · regressed < 0.70 or worse than baseline · inconclusive when the upstream's own gain is
within run-to-run noise (|gain| < 2 × pooled stdev). Never rounds "near" up to "same".
"""
import math

SAME, NEAR = 0.90, 0.70
EPS = 1e-9


def mean(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else None


def stdev(xs):
    xs = [x for x in xs if x is not None]
    if len(xs) < 2:
        return 0.0
    m = sum(xs) / len(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - 1))


def pooled_stdev(*groups):
    """Pooled sample stdev over groups with ≥ 2 runs (0.0 when no group has a spread to measure)."""
    num = den = 0.0
    for g in groups:
        g = [x for x in g if x is not None]
        if len(g) >= 2:
            num += (len(g) - 1) * stdev(g) ** 2
            den += len(g) - 1
    return math.sqrt(num / den) if den else 0.0


def verdict(baseline, upstream, agylite, lower_is_better=False):
    """Verdict for one metric from its per-run values in each arm (lists, or single numbers)."""
    as_list = lambda v: list(v) if isinstance(v, (list, tuple)) else [v]   # noqa: E731
    b, u, a = (as_list(v) for v in (baseline, upstream, agylite))
    mb, mu, ma = mean(b), mean(u), mean(a)
    out = {"baseline": mb, "upstream": mu, "agylite": ma, "n": min(len(b), len(u), len(a)),
           "lower_is_better": lower_is_better}
    if None in (mb, mu, ma):
        return {**out, "retained": None, "verdict": "missing"}
    sign = -1 if lower_is_better else 1
    gain_u, gain_a = sign * (mu - mb), sign * (ma - mb)
    noise = pooled_stdev(b, u, a)
    out.update(gain_upstream=gain_u, gain_agylite=gain_a, pooled_stdev=noise)
    if abs(gain_u) < EPS:
        # The original adds nothing over no skill here (e.g. both pass a gate): Agylite must not be worse.
        return {**out, "retained": None, "verdict": "same" if gain_a >= -EPS else "regressed",
                "note": "no upstream gain to retain"}
    if noise and abs(gain_u) < 2 * noise:
        return {**out, "retained": round(gain_a / gain_u, 3), "verdict": "inconclusive",
                "note": "upstream gain within run-to-run noise"}
    retained = gain_a / gain_u
    if gain_u > 0 and gain_a < -EPS:
        v = "regressed"   # worse than no skill
    elif retained >= SAME - 1e-6:   # float noise: (2.9 − 2) ÷ (3 − 2) is 0.8999…, which is 0.90
        v = "same"
    elif retained >= NEAR - 1e-6:
        v = "near"
    else:
        v = "regressed"
    return {**out, "retained": round(retained, 3), "verdict": v}


ORDER = {"regressed": 0, "missing": 0, "inconclusive": 1, "near": 2, "same": 3}


def suite_verdict(metric_verdicts: dict) -> str:
    """A suite is only as good as its weakest metric."""
    vs = [m["verdict"] for m in metric_verdicts.values()]
    return min(vs, key=lambda v: ORDER.get(v, 0)) if vs else "missing"
