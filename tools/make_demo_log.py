#!/usr/bin/env python3
"""Make a realistic NAZAR inspection log (contract section 5 request shape) for demos and tests.

Stories:
  loose-mount  The motor mount works loose: shaking episodes get longer and rejects rise
               while it shakes. Then maintenance tightens the mount (fix_at); after that
               shaking and rejects drop. Expected agent answer: cause = vib, fix worked.
  no-cause     Rejects are random (bad incoming washers). The sensors do go amber now and then,
               but rejects do not follow them. Expected: no machine cause, said honestly.
  dim-light    The tunnel LED dims for a while; rejects rise in the dark. Expected: cause = lux.
  few          Only 12 washers. Expected: enough = false.

    python tools/make_demo_log.py --story loose-mount -o demo.json
"""
import argparse
import datetime
import json
import os
import random
import sys

LIMITS = {"vib": {"amber": 0.08, "red": 0.15}, "lux": {"amber": 300, "red": 120},
          "temp": {"amber": 45, "red": 60}, "ma": {"amber": 700, "red": 1000}}


def _start_ms():
    today = datetime.date.today()
    return int(datetime.datetime(today.year, today.month, today.day, 10, 0).timestamp() * 1000)


def _verdict(rng, p_reject, p_hold):
    x = rng.random()
    if x < p_reject:
        return "REJECT", round(rng.uniform(0.45, 0.78), 3)
    if x < p_reject + p_hold:
        return "HOLD", round(rng.uniform(0.33, 0.44), 3)
    return "PASS", round(rng.uniform(0.10, 0.31), 3)


def _row(rng, at, n, vib, lux, temp, ma, p_reject, p_hold):
    verdict, score = _verdict(rng, p_reject, p_hold)
    row = {"at": at, "n": n, "verdict": verdict, "score": score, "ms": rng.randint(38, 72),
           "v": round(rng.gauss(11.92, 0.04), 2), "ma": round(ma, 1), "vib": round(max(0.008, vib), 3),
           "vpk": round(max(0.02, vib * rng.gauss(2.6, 0.3)), 3), "lux": round(lux, 1), "temp": round(temp, 1)}
    if rng.random() < 0.02:          # DS18B20 drops out now and then: the key is simply missing
        del row["temp"]
    return row


def loose_mount(rng, start):
    episodes = [(40, 62), (105, 140), (165, 214)]          # the mount gets worse: longer shaking spells
    fix_part, total = 220, 300
    rows, at, fix_at = [], start, None
    for n in range(1, total + 1):
        at += int(rng.uniform(7000, 13000))
        if n == fix_part:                                   # 4 min stop to tighten the mount
            fix_at = at + 30000
            at += 240000
        shaking = any(a <= n <= b for a, b in episodes)
        if shaking:
            vib = rng.gauss(0.12, 0.028)
        elif n >= fix_part:
            vib = rng.gauss(0.030, 0.007) if rng.random() > 0.02 else rng.gauss(0.09, 0.01)
        else:
            vib = rng.gauss(0.036, 0.009)
        hard = vib > 0.08
        rows.append(_row(rng, at, n, vib, rng.gauss(812, 22), 33.0 + min(6.0, n * 0.025) + rng.gauss(0, 0.3),
                         rng.gauss(330, 18) + (18 if shaking else 0),
                         0.30 if hard else 0.035, 0.07 if hard else 0.015))
    # a couple of empty frames: NO_PART must be ignored, never counted as a defect
    for k in (77, 181):
        r = dict(rows[k], verdict="NO_PART", score=0.0, n=None)
        rows.insert(k, r)
    return rows, fix_at, "tightened motor mount screws, added thread-locker"


def no_cause(rng, start):
    rows, at = [], start
    for n in range(1, 241):
        at += int(rng.uniform(7000, 13000))
        vib = rng.gauss(0.12, 0.02) if 50 <= n <= 74 else rng.gauss(0.036, 0.009)
        lux = rng.gauss(255, 20) if 120 <= n <= 141 else rng.gauss(810, 22)
        temp = rng.gauss(47.5, 0.8) if 170 <= n <= 196 else rng.gauss(36, 0.6)
        ma = rng.gauss(760, 30) if rng.random() < 0.09 else rng.gauss(330, 18)
        rows.append(_row(rng, at, n, vib, lux, temp, ma, 0.075, 0.02))
    return rows, None, ""


def dim_light(rng, start):
    rows, at = [], start
    for n in range(1, 201):
        at += int(rng.uniform(7000, 13000))
        dim = 90 <= n <= 135
        lux = rng.gauss(240, 30) if dim else rng.gauss(805, 25)
        dark = lux < 300
        rows.append(_row(rng, at, n, rng.gauss(0.036, 0.009), lux, rng.gauss(36, 0.6), rng.gauss(330, 18),
                         0.28 if dark else 0.04, 0.08 if dark else 0.015))
    return rows, None, ""


def few(rng, start):
    rows, at = [], start
    for n in range(1, 13):
        at += int(rng.uniform(7000, 13000))
        rows.append(_row(rng, at, n, rng.gauss(0.036, 0.009), rng.gauss(810, 22), 35.0, rng.gauss(330, 18), 0.1, 0.0))
    return rows, None, ""


STORIES = {"loose-mount": loose_mount, "no-cause": no_cause, "dim-light": dim_light, "few": few}


def make(story="loose-mount", seed=42, lang="en", use_llm=True, start=None):
    rng = random.Random(seed)
    rows, fix_at, note = STORIES[story](rng, start or _start_ms())
    req = {"lang": lang, "use_llm": use_llm, "source": "demo", "limits": LIMITS}
    if fix_at:
        req["fix_at"], req["fix_note"] = fix_at, note
    req["inspections"] = rows
    return req


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--story", choices=sorted(STORIES), default="loose-mount")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--lang", choices=["en", "hi"], default="en")
    ap.add_argument("--no-llm", action="store_true", help="set use_llm:false in the request")
    ap.add_argument("-o", "--out", help="output file (default: stdout)")
    a = ap.parse_args()
    req = make(a.story, a.seed, a.lang, not a.no_llm)
    data = json.dumps(req, indent=1, ensure_ascii=False)
    if a.out:
        os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
        with open(a.out, "w", encoding="utf-8") as f:
            f.write(data)
        print(f"{a.out}: {len(req['inspections'])} rows, story {a.story}", file=sys.stderr)
    else:
        print(data)


if __name__ == "__main__":
    main()
