"""Statistics on the inspection log (standard library only).

  * p-chart: the log is cut into windows of equal size; each window's defect share is
    compared with the overall share +- 3 sigma (classic SPC attribute chart).
  * Stratification: for every sensor, washers are split into "in the amber state"
    (vib/temp/ma above amber, lux BELOW amber) and "normal", and the two defect rates are
    compared: rate ratio + two-sided Fisher exact p-value.
  * Cause: the factor with a clear, significant link (Bonferroni over the factors tested).
  * Before/after: around fix_at, both the defect rate and how often the cause state occurs.

A washer counts as "bad" when the camera said REJECT or HOLD. NO_PART rows and rows
without a usable verdict or time are ignored (NO_PART is never a defect, contract section 4).
"""
import math

from .knowledge import BY_KEY, FACTORS

MIN_ROWS = 20          # below this: enough=false, no report
MIN_GROUP = 5          # a sensor state needs this many washers on each side to be compared
MIN_AFTER = 10         # washers needed after the fix before judging it
ALPHA = 0.05
MIN_RATIO = 2.0        # "clearly more rejects": at least twice the normal rate
BAD = {"REJECT", "HOLD"}
GOOD = {"PASS"}


# ---------------------------------------------------------------- input
def _num(x):
    if isinstance(x, bool) or x is None:
        return None
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) else None


def clean_rows(raw):
    """Usable rows sorted by time, and how many were ignored."""
    rows, ignored = [], 0
    for r in raw if isinstance(raw, list) else []:
        if not isinstance(r, dict):
            ignored += 1
            continue
        verdict = str(r.get("verdict", "")).strip().upper()
        at = _num(r.get("at"))
        if verdict not in BAD | GOOD or at is None:
            ignored += 1
            continue
        row = {"at": at, "n": r.get("n"), "verdict": verdict, "bad": verdict in BAD}
        for f in FACTORS:
            v = _num(r.get(f.key))
            if v is not None:
                row[f.key] = v
        rows.append(row)
    rows.sort(key=lambda x: x["at"])
    return rows, ignored


def amber_limits(limits):
    """{key: amber} from the request, falling back to the console defaults."""
    out = {}
    limits = limits if isinstance(limits, dict) else {}
    for f in FACTORS:
        L = limits.get(f.key)
        a = _num(L.get("amber")) if isinstance(L, dict) else None
        out[f.key] = a if a is not None else f.amber
    return out


def in_state(row, key, amber):
    """True/False whether this washer was inspected in the factor's amber state; None if not measured."""
    v = row.get(key)
    if v is None:
        return None
    return v < amber if BY_KEY[key].side == "low" else v > amber


# ---------------------------------------------------------------- tests
def _logcomb(n, k):
    return math.lgamma(n + 1) - math.lgamma(k + 1) - math.lgamma(n - k + 1)


def fisher_exact(a, b, c, d):
    """Two-sided Fisher exact test for the 2x2 table [[a, b], [c, d]].

    With the row and column totals fixed, every possible table has a hypergeometric
    probability; the p-value adds up all tables at most as likely as the one observed.
    """
    r1, r2, c1 = a + b, c + d, a + c
    n = r1 + r2
    if min(a, b, c, d) < 0 or r1 == 0 or r2 == 0 or c1 == 0 or c1 == n:
        return 1.0
    lo, hi = max(0, c1 - r2), min(c1, r1)
    base = _logcomb(n, c1)

    def logp(x):
        return _logcomb(r1, x) + _logcomb(r2, c1 - x) - base

    seen = logp(a)
    total = sum(math.exp(logp(x)) for x in range(lo, hi + 1) if logp(x) <= seen + 1e-7)
    return min(1.0, total)


def _sig4(p):
    return float(f"{p:.4g}")


def rate_ratio(hb, hn, lb, ln):
    """Defect rate in the state / defect rate outside it (0.5 continuity correction if the latter is 0)."""
    if not hn or not ln:
        return None
    if lb == 0:
        return ((hb + 0.5) / (hn + 1)) / ((lb + 0.5) / (ln + 1))
    return (hb / hn) / (lb / ln)


# ---------------------------------------------------------------- pieces
def p_chart(rows, pbar):
    n = len(rows)
    size = 20 if n <= 400 else math.ceil(n / 20)
    chunks = [rows[i:i + size] for i in range(0, n, size)]
    if len(chunks) > 1 and len(chunks[-1]) < size / 2:       # a stub at the end joins the window before it
        chunks[-2].extend(chunks.pop())
    out = []
    for ch in chunks:
        m, bad = len(ch), sum(r["bad"] for r in ch)
        sigma = math.sqrt(pbar * (1 - pbar) / m)
        p = bad / m
        ucl, lcl = min(1.0, pbar + 3 * sigma), max(0.0, pbar - 3 * sigma)
        out.append({"from": int(ch[0]["at"]), "to": int(ch[-1]["at"]), "n": m, "bad": bad, "p": round(p, 4),
                    "ucl": round(ucl, 4), "lcl": round(lcl, 4), "out": p > ucl})
    return out


def stratify(rows, ambers):
    strata = []
    for f in FACTORS:
        have = [r for r in rows if f.key in r]
        if not have:
            continue
        amber = ambers[f.key]
        high = [r for r in have if in_state(r, f.key, amber)]
        low = [r for r in have if not in_state(r, f.key, amber)]
        hb, lb = sum(r["bad"] for r in high), sum(r["bad"] for r in low)
        s = {"factor": f.key, "label": None, "side": f.side, "amber": amber, "unit": f.unit,
             "high_n": len(high), "high_bad": hb, "low_n": len(low), "low_bad": lb,
             "high_rate": round(hb / len(high), 4) if high else None,
             "low_rate": round(lb / len(low), 4) if low else None,
             "ratio": None, "p_value": None,
             "testable": len(high) >= MIN_GROUP and len(low) >= MIN_GROUP, "significant": False}
        if s["testable"]:
            s["ratio"] = round(rate_ratio(hb, len(high), lb, len(low)), 2)
            s["p_value"] = _sig4(fisher_exact(hb, len(high) - hb, lb, len(low) - lb))
        strata.append(s)
    tested = [s for s in strata if s["testable"]]
    alpha_each = ALPHA / max(1, len(tested))           # Bonferroni: 4 sensors = 4 chances of a fluke
    for s in tested:
        s["significant"] = s["p_value"] < alpha_each and s["ratio"] >= MIN_RATIO and s["high_bad"] >= 3
    return strata, alpha_each


def pick_cause(strata):
    """(cause, hint): cause = the significant factor with the smallest p; hint = a weaker lead if none is."""
    sig = [s for s in strata if s["significant"]]
    if sig:
        return min(sig, key=lambda s: (s["p_value"], -s["ratio"]))["factor"], None
    lead = [s for s in strata if s["testable"] and s["ratio"] >= MIN_RATIO and s["p_value"] < 0.1 and s["high_bad"] >= 3]
    return None, (min(lead, key=lambda s: s["p_value"])["factor"] if lead else None)


def before_after(rows, fix_at, fix_note, key, amber):
    before = [r for r in rows if r["at"] < fix_at]
    after = [r for r in rows if r["at"] >= fix_at]
    bb, ab = sum(r["bad"] for r in before), sum(r["bad"] for r in after)
    out = {"fix_at": int(fix_at), "fix_note": fix_note,
           "before_n": len(before), "before_bad": bb, "after_n": len(after), "after_bad": ab,
           "before_rate": round(bb / len(before), 4) if before else None,
           "after_rate": round(ab / len(after), 4) if after else None,
           "p_rate": _sig4(fisher_exact(bb, len(before) - bb, ab, len(after) - ab)) if before and after else None,
           "cause_factor": key, "cause_before": None, "cause_after": None, "p_cause": None}
    if key:
        sb = [in_state(r, key, amber) for r in before if key in r]
        sa = [in_state(r, key, amber) for r in after if key in r]
        if sb and sa:
            out["cause_before"] = round(sum(sb) / len(sb), 4)
            out["cause_after"] = round(sum(sa) / len(sa), 4)
            out["p_cause"] = _sig4(fisher_exact(sum(sb), len(sb) - sum(sb), sum(sa), len(sa) - sum(sa)))
    out["verdict"] = _fix_verdict(out)
    return out


def _fix_verdict(o):
    if not o["before_n"]:
        return "no-before"
    if o["after_n"] < MIN_AFTER:
        return "wait"
    rate_down = o["p_rate"] < ALPHA and o["after_rate"] < o["before_rate"]
    rate_up = o["p_rate"] < ALPHA and o["after_rate"] > o["before_rate"]
    cause_gone = (o["p_cause"] is not None and o["p_cause"] < ALPHA
                  and o["cause_after"] <= o["cause_before"] / 2)
    if rate_up:
        return "worse"
    if rate_down:
        return "worked"
    if cause_gone and o["after_rate"] <= o["before_rate"]:
        return "cause-removed"          # the cause state is gone; the rate is lower but not yet provably
    return "unclear"


# ---------------------------------------------------------------- all of it
def analyse(req):
    rows, ignored = clean_rows(req.get("inspections"))
    n, bad = len(rows), sum(r["bad"] for r in rows)
    s = {"n": n, "bad": bad, "rate": round(bad / n, 4) if n else 0.0,
         "reject": sum(r["verdict"] == "REJECT" for r in rows), "hold": sum(r["verdict"] == "HOLD" for r in rows),
         "ignored": ignored, "need": MIN_ROWS}
    if n:
        s["from"], s["to"] = int(rows[0]["at"]), int(rows[-1]["at"])
        s["minutes"] = max(1, round((rows[-1]["at"] - rows[0]["at"]) / 60000))
    if n < MIN_ROWS:
        return s, False
    ambers = amber_limits(req.get("limits"))
    pbar = bad / n
    s["pbar"] = round(pbar, 4)
    s["pchart"] = p_chart(rows, pbar)
    s["strata"], s["alpha_each"] = stratify(rows, ambers)
    s["cause"], s["hint"] = pick_cause(s["strata"])
    fix_at = _num(req.get("fix_at"))
    if fix_at is not None:
        key = s["cause"] or s["hint"]
        note = req.get("fix_note") if isinstance(req.get("fix_note"), str) else ""
        s["before_after"] = before_after(rows, fix_at, note.strip()[:200], key, ambers.get(key))
    else:
        s["before_after"] = None
    return s, True
