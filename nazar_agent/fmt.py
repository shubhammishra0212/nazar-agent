"""How numbers are written in reports.

Every number in a report goes through these functions, so the LLM number checker
can compare like with like (the same value is always spelled the same way).
"""
import datetime


def pct(x):
    """0.117 -> '12', 0.044 -> '4.4', 0 -> '0' (percent, no sign)."""
    if x is None:
        return "-"
    v = x * 100
    if v == 0:
        return "0"
    return f"{v:.0f}" if v >= 10 else f"{v:.1f}"


def ratio(x):
    return "-" if x is None else f"{x:.1f}"


def pval(p):
    """Plain p-value text, e.g. 'p < 0.001' or 'p = 0.004'."""
    if p is None:
        return "p = -"
    if p < 0.001:
        return "p < 0.001"
    return f"p = {p:.3f}" if p < 0.1 else f"p = {p:.2f}"


def clock(ms):
    """Unix ms -> local 'HH:MM'."""
    return datetime.datetime.fromtimestamp(ms / 1000).strftime("%H:%M")


def value(x, dec):
    return f"{x:.{dec}f}"
