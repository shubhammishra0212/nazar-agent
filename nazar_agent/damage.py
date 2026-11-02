"""8D about the damage itself: which washers were rejected, what the damage is, where, and what usually causes it.

Used when the request asks for it (focus "damage") or when there are too few washers for the statistics but some
rejected washers carry a damage description from the vision service (kind, spots, where, area). Same draft shape as
report.draft(), so the LLM may reword the same explanation sections (5-Why, D5, D7, D8) under the same checks.
English only. Texts here carry no numbers on purpose: every number comes from the inspection log.
"""
from . import fmt

# what each kind of damage usually means for a washer, and what to do about it
KNOW = {
    "dent": {
        "what": "pressed-in round marks (dents) on the face",
        "cause": "the face was struck or pressed by something hard after pressing: washers knocking into each other "
                 "and into metal bin edges when they are tipped or dropped in bulk, or a hard particle caught in the "
                 "punching or flattening tool",
        "why": ["Why was the washer rejected? The camera found pressed-in dents on its face that good washers do not have.",
                "Why does the face have dents? Something hard hit or pressed the face after the washer was made.",
                "Why was it hit? Washers knock into each other and into metal bin edges when they are tipped in bulk.",
                "Why are they tipped in bulk? Washers move between stations by pouring from a height, with no padded "
                "chute or tray.",
                "Why was it not caught earlier? Nothing checks the face between the press and this station."],
        "act": "Maintenance checks the punching and flattening tools for a chip or hard particle stuck on the face "
               "and cleans them. The operator lowers the drop height and pours washers onto a padded chute or into "
               "trays instead of tipping bins. Quality checks the next lot for dents.",
        "prevent": "Use padded bins and trays for every transfer, write the drop height into the work instruction "
                   "and clean the press tooling at every shift start.",
    },
    "scar": {
        "what": "a scar (gouge and scratch) running out from the hole edge across the face",
        "cause": "a sharp edge was dragged across the washer: a burr left by the punch at the hole, washers sliding "
                 "over a worn sharp guide or chute edge, or a bolt thread dragged through the hole",
        "why": ["Why was the washer rejected? The camera found a scar running out from the hole edge that good washers "
                "do not have.",
                "Why is there a scar? A hard, sharp edge was dragged across the face near the hole.",
                "Why was a sharp edge dragged across it? Washers slide over guides and over each other, and a burr or "
                "sharp corner digs in.",
                "Why is there a sharp edge? The punch leaves a burr at the hole, or a guide or chute edge has worn sharp.",
                "Why was it not caught earlier? Nothing checks the face between the press and this station."],
        "act": "Maintenance deburrs or replaces the hole punch and rounds off any sharp guide or chute edge the washers "
               "slide over. The operator keeps washers apart in trays so they do not slide on each other. Quality "
               "checks the next lot for scars at the hole.",
        "prevent": "Add punch wear and burr height to the daily tool check, and round and polish every guide edge.",
    },
    "other": {
        "what": "surface damage that good washers do not have",
        "cause": "the washer was hit, scraped or marked after pressing, during handling or transfer",
        "why": ["Why was the washer rejected? The camera found surface damage that good washers do not have.",
                "Why is there damage? The face was hit or scraped after the washer was made.",
                "Why was it hit or scraped? Washers touch hard and sharp surfaces during handling and transfer.",
                "Why do they touch hard surfaces? Transfer between stations is not protected by padded chutes or trays.",
                "Why was it not caught earlier? Nothing checks the face between the press and this station."],
        "act": "Maintenance checks the press tooling and every surface the washers touch on the way to this station. "
               "The operator moves washers in trays. Quality checks the next lot by hand.",
        "prevent": "Protect every transfer with padded chutes or trays.",
    },
}
MIXED_WHY = [
    "Why were these washers rejected? The camera found damage on their faces that good washers do not have.",
    "Why are the faces damaged? Hard and sharp objects hit or scraped them after the washers were made.",
    "Why were they hit and scraped? Washers knock into each other, into bin edges and over sharp guide edges when "
    "they are tipped and slid in bulk.",
    "Why is that possible? Transfer between stations is done by pouring from a height, and the punch and guides "
    "leave burrs and sharp corners.",
    "Why was it not caught earlier? Nothing checks the face between the press and this station.",
]
SENSORS = [("vib", "motor shaking", "high", 3, "g"), ("lux", "tunnel light", "low", 0, "lx"),
           ("temp", "motor temperature", "high", 1, "°C"), ("ma", "motor current", "high", 0, "mA")]


def damaged_rows(req):
    """Rejected rows that carry a damage description, oldest first."""
    rows = [r for r in (req.get("inspections") or []) if isinstance(r, dict)
            and r.get("verdict") == "REJECT" and isinstance(r.get("damage"), dict)]
    return sorted(rows, key=lambda r: r.get("at") or 0)


def wanted(req, enough):
    focus = str(req.get("focus") or "").lower()
    return bool(damaged_rows(req)) and (focus == "damage" or not enough)


def _kind(r):
    k = str(r["damage"].get("kind") or "other").lower()
    return k if k in KNOW else "other"


def _line_state(rows, limits):
    """Sentence on the machine sensors at the moments the damaged washers were inspected."""
    past = []
    for key, name, side, dec, unit in SENSORS:
        amber = ((limits or {}).get(key) or {}).get("amber")
        vals = [r[key] for r in rows if isinstance(r.get(key), (int, float))]
        if amber is None or not vals:
            continue
        hit = [v for v in vals if (v <= amber if side == "low" else v >= amber)]
        if hit:
            past.append(f"{name} was past its amber limit ({fmt.value(amber, dec)} {unit})")
    if past:
        return (" When they were inspected, " + " and ".join(past) + ", so the line itself may have added to the "
                "damage; check that too.")
    return (" The line sensors (motor shaking, light, temperature, motor current) were inside their limits when "
            "these washers were inspected, so the damage was most likely done before the washers reached the conveyor.")


def draft(req, s, source="live"):
    rows = damaged_rows(req)
    kinds = []
    for r in rows:
        if _kind(r) not in kinds:
            kinds.append(_kind(r))
    labels = [str(r["damage"].get("label") or _kind(r).capitalize()) for r in rows]
    names = []
    for lab in labels:
        if lab.lower() not in [x.lower() for x in names]:
            names.append(lab)
    n_all, n_rej = s["n"], len(rows)

    def one(r):
        d = r["damage"]
        spots = int(d.get("spots") or 1)
        bits = [f"Washer {r.get('n')}: {str(d.get('label') or 'damage').lower()}"
                + (f", {spots} spots" if spots > 1 else ""),
                f"strongest at the {d.get('where') or 'face'}"]
        if isinstance(d.get("area_pct"), (int, float)):
            bits.append(f"about {fmt.value(d['area_pct'], 1)}% of the face")
        if isinstance(r.get("score"), (int, float)):
            bits.append(f"AI score {fmt.value(r['score'], 2)}")
        return ", ".join(bits)

    title = "Damaged washers rejected: " + " and ".join(x.lower() for x in names)
    summary = (f"{n_all} washers inspected; the AI found {n_rej} damaged ({', '.join(x.lower() for x in labels)}) and "
               f"the reject gate pushed them off the line.")
    d1 = ("Team Parakh: line operator (runs the belt, keeps the rejected washers), maintenance (press tooling and "
          f"conveyor) and quality (the NAZAR inspection station, owns this report). Data: NAZAR inspection log ({source}).")
    n_all = max(n_all, n_rej)
    t_from = s.get("from") or min(r.get("at") or 0 for r in rows)
    t_to = s.get("to") or max(r.get("at") or 0 for r in rows)
    when = (f"at {fmt.clock(t_from)}" if fmt.clock(t_from) == fmt.clock(t_to)
            else f"between {fmt.clock(t_from)} and {fmt.clock(t_to)}")
    d2 = (f"NAZAR inspected {n_all} washers {when} and rejected "
          f"{n_rej} for visible damage. " + "; ".join(one(r) for r in rows) + ". "
          + " ".join(f"{k.capitalize()}: {KNOW[k]['what']}." for k in kinds)
          + (f" The other {n_all - n_rej - s['hold']} washers passed." if n_all - n_rej - s["hold"] > 0 else ""))
    d3 = ("The reject gate pushed each damaged washer off the line as soon as the AI judged it, so none went on with "
          "the good parts. Keep the rejected washers apart, labelled with their part numbers, for the hand check. "
          "Hold the rest of the same lot and run it through NAZAR before it is shipped.")
    d4 = " ".join(f"{k.capitalize()}: most likely {KNOW[k]['cause']}." for k in kinds)
    d4 += (" This is read from the shape and position of the damage; confirm it at the press and along the "
           "handling path." + _line_state(rows, req.get("limits")))
    d6 = ("Run the next lot through NAZAR after the actions in D5 and press Mark fix applied when they are done, so the "
          "reject rate before and after can be compared. The fix works when no new washers with "
          + " or ".join(x.lower() for x in names) + " are found.")
    why = list(KNOW[kinds[0]]["why"]) if len(kinds) == 1 else list(MIXED_WHY)
    d5 = " ".join(KNOW[k]["act"] for k in kinds)
    d7 = " ".join(KNOW[k]["prevent"] for k in kinds) + " Keep NAZAR checking every washer."
    d8 = ("Close this 8D when a full lot has run through NAZAR after the actions with no new damaged washers, and "
          "quality has checked the rejected washers by hand and confirmed the damage. Thank the operator and "
          "maintenance team.")
    return {"title": title, "summary": summary, "D1": d1, "D2": d2, "D3": d3, "D4": d4, "D6": d6,
            "why": why, "D5": d5, "D7": d7, "D8": d8}


def evidence(req):
    """What the console shows next to the report: one entry per damaged washer."""
    out = []
    for r in damaged_rows(req):
        d = r["damage"]
        out.append({"n": r.get("n"), "at": r.get("at"), "score": r.get("score"), "kind": d.get("kind"),
                    "label": d.get("label"), "spots": d.get("spots"), "where": d.get("where"),
                    "area_pct": d.get("area_pct"), "match": d.get("match")})
    return out
