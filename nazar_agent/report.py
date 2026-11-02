"""8D report templates, English and Hindi.

draft(stats, lang) returns a complete 8D written only from the statistics and knowledge.py.
It has two kinds of parts:

  FACTS  title, summary, D1, D2, D3, D4, D6   always from here, never from the LLM
  EXPLAIN  why (5-Why chain), D5, D7, D8      the LLM may reword these (llm.py)

so a report is always complete and correct even when the LLM is off, missing or wrong.
"""
import re

from . import fmt
from .knowledge import BY_KEY, SECTION_TITLES, text
from .stats import MIN_AFTER, MIN_GROUP

FACT_KEYS = ["title", "summary", "D1", "D2", "D3", "D4", "D6"]
EXPLAIN_KEYS = ["WHY1", "WHY2", "WHY3", "WHY4", "WHY5", "D5", "D7", "D8"]


def _stratum(s, key):
    return next((x for x in s.get("strata", []) if x["factor"] == key), None)


def _amber(st):
    f = BY_KEY[st["factor"]]
    return f"{fmt.value(st['amber'], f.dec)} {f.unit}"


def _untested(s, key, lang):
    """Sentence naming the sensors that never had enough washers in their amber state to be compared."""
    names = [text(lang, x["factor"])["label"] for x in s["strata"] if not x["testable"] and x["factor"] != key]
    if not names:
        return ""
    if lang == "hi":
        return f" {', '.join(names)}: पीली स्थिति में बहुत कम वॉशर थे, इसलिए इनकी तुलना नहीं हो सकी।"
    joined = ", ".join(n.lower() for n in names)
    return f" Not testable ({joined}): too few washers were inspected in their amber state."


def _source(s):
    src = re.sub(r"[^A-Za-z0-9 _-]", "", str(s or "live"))[:20]
    return src or "live"


def _verdict_key(s):
    ba = s.get("before_after")
    return ba["verdict"] if ba else None


# ================================================================ English
def _facts_en(s, source):
    key = s["cause"] or s["hint"]
    K = text("en", key)
    st = _stratum(s, key) if key else None
    pc = s["pchart"]
    outs = [w for w in pc if w["out"]]

    d2 = [f"Between {fmt.clock(s['from'])} and {fmt.clock(s['to'])} ({s['minutes']} min), NAZAR inspected "
          f"{s['n']} washers: {s['reject']} were rejected and {s['hold']} held for a check, so {fmt.pct(s['rate'])}% "
          f"were flagged."]
    if outs:
        d2.append(f"The flagged rate went above its 3-sigma control limit in {len(outs)} of {len(pc)} windows, "
                  f"first in the window starting {fmt.clock(outs[0]['from'])}.")
    else:
        d2.append(f"The flagged rate stayed inside its 3-sigma control limits in all {len(pc)} windows.")
    if st:
        d2.append(f"While {K['state']} ({_amber(st)}), {fmt.pct(st['high_rate'])}% of washers were flagged "
                  f"({st['high_bad']} of {st['high_n']}), against {fmt.pct(st['low_rate'])}% otherwise "
                  f"({st['low_bad']} of {st['low_n']}).")

    d3 = (f"So far the gate removed {s['reject']} washers and {s['hold']} were held for a hand check. "
          + text("en", s["cause"])["contain"] if not s["hint"] else
          f"So far the gate removed {s['reject']} washers and {s['hold']} were held for a hand check. "
          f"Keep every washer going through the camera and check held washers by hand until the cause is confirmed.")

    others = [x for x in s["strata"] if x["testable"] and x["factor"] != key]
    other_txt = "; ".join(f"{text('en', x['factor'])['label'].lower()}: {fmt.pct(x['high_rate'])}% in the amber "
                          f"state against {fmt.pct(x['low_rate'])}% otherwise" for x in others)
    if s["cause"]:
        d4 = (f"{K['cause']} Evidence: {fmt.pct(st['high_rate'])}% of washers were flagged while {K['state']}, against "
              f"{fmt.pct(st['low_rate'])}% otherwise: {fmt.ratio(st['ratio'])} times the normal rate (Fisher's exact test, "
              f"{fmt.pval(st['p_value'])}).")
        if other_txt:
            d4 += f" The other sensors showed no clear link ({other_txt})."
        d4 += _untested(s, key, "en")
    elif s["hint"]:
        d4 = (f"Not proven yet. The data points to {K['fault']}: {fmt.pct(st['high_rate'])}% of washers were flagged "
              f"while {K['state']}, against {fmt.pct(st['low_rate'])}% otherwise ({fmt.ratio(st['ratio'])} times), but "
              f"with {s['n']} washers this could still be chance ({fmt.pval(st['p_value'])}). Keep the line running "
              f"and run the agent again with more washers.")
    else:
        all_txt = "; ".join(f"{text('en', x['factor'])['label'].lower()}: {fmt.pct(x['high_rate'])}% in the amber "
                            f"state against {fmt.pct(x['low_rate'])}% otherwise ({fmt.pval(x['p_value'])})"
                            for x in s["strata"] if x["testable"])
        d4 = K["cause"] + (f" Evidence from {s['n']} washers: {all_txt}." if all_txt else
                           f" There were too few washers in any amber state to compare (each side needs at least "
                           f"{MIN_GROUP}).")
        d4 += _untested(s, None, "en") if all_txt else ""

    d6 = _d6_en(s)
    title = (K["title"] if not s["hint"] else f"Possible cause: {K['label'].lower()} (not proven yet)")
    summary = f"{s['n']} washers inspected, {s['bad']} flagged ({fmt.pct(s['rate'])}%)."
    if s["cause"]:
        summary += (f" Washers were flagged {fmt.ratio(st['ratio'])} times as often while {K['state']} "
                    f"({fmt.pval(st['p_value'])}). Most likely cause: {K['fault']}.")
    elif s["hint"]:
        summary += f" Possible link to {K['label'].lower()}, not proven yet."
    else:
        summary += " No machine state explains the rejects."
    ba = s.get("before_after")
    if ba and ba["verdict"] not in ("wait", "no-before"):
        summary += (f" After the fix the flagged rate went from {fmt.pct(ba['before_rate'])}% to "
                    f"{fmt.pct(ba['after_rate'])}%.")
    d1 = ("Team Parakh: line operator (runs the belt and acts on alarms), maintenance (mechanical and electrical "
          "fixes) and quality (the NAZAR inspection station, owns this report). "
          f"Data: NAZAR inspection log ({source}).")
    return {"title": title, "summary": summary, "D1": d1, "D2": " ".join(d2), "D3": d3, "D4": d4, "D6": d6}


def _d6_en(s):
    ba = s.get("before_after")
    key = s["cause"] or s["hint"]
    label = text("en", key)["label"].lower() if key else "machine state"
    if not ba:
        return ("Not done yet. After the fix, mark the fix time in the console, run more washers and generate this "
                f"report again: NAZAR then compares the flagged rate and the {label} state before and after the fix.")
    out = f"Fix marked at {fmt.clock(ba['fix_at'])}" + (f": {ba['fix_note']}." if ba["fix_note"] else ".")
    if ba["before_n"] and ba["after_n"]:
        if ba["cause_before"] is not None:
            out += (f" Before the fix, {fmt.pct(ba['cause_before'])}% of washers were inspected in the {label} amber "
                    f"state; after it, {fmt.pct(ba['cause_after'])}%.")
        out += (f" Flagged washers: {ba['before_bad']} of {ba['before_n']} before ({fmt.pct(ba['before_rate'])}%), "
                f"{ba['after_bad']} of {ba['after_n']} after ({fmt.pct(ba['after_rate'])}%).")
    v = ba["verdict"]
    out += {
        "no-before": " No washers were inspected before the fix, so there is nothing to compare.",
        "wait": f" Too early to judge: at least {MIN_AFTER} washers are needed after the fix (now {ba['after_n']}).",
        "worked": f" The flagged rate fell clearly (Fisher's exact test, {fmt.pval(ba['p_rate'])}): the fix worked.",
        "cause-removed": f" The cause state is clearly gone ({fmt.pval(ba['p_cause'])}) and the flagged rate is lower, "
                         f"though not yet provably ({fmt.pval(ba['p_rate'])}): the fix looks effective; keep watching.",
        "worse": f" The flagged rate went up after the fix ({fmt.pval(ba['p_rate'])}): the fix did not remove the "
                 f"cause; look again.",
        "unclear": f" No clear change yet ({fmt.pval(ba['p_rate'])}). Keep watching, or look for another cause.",
    }[v]
    return out


def _explain_en(s):
    key = s["cause"] or s["hint"]
    K = text("en", key)
    v = _verdict_key(s)
    if s["hint"]:
        d8 = "Do not close yet: run more washers and generate the report again to confirm the cause first."
    elif not s["cause"]:
        d8 = ("Close this 8D only after the batch check confirms where the defects come from; then record the lesson "
              "and thank the team.")
    elif v == "worked":
        d8 = ("Close the 8D: the data shows the fix worked. Record the fix in the maintenance log, add the new checks "
              "to the shift checklist and thank the operator, maintenance and quality team.")
    elif v == "cause-removed":
        d8 = ("Keep the 8D open for one more shift to confirm the lower rate, then close it, record the fix and "
              "thank the team.")
    else:
        d8 = ("Keep the 8D open. Close it once the flagged rate stays inside its control limits for a full shift "
              "after the fix, then record the lesson and thank the team.")
    d5 = ("Check first, then act. " + K["act"]) if s["hint"] else K["act"]
    return {"why": list(K["why"]), "D5": d5, "D7": K["prevent"], "D8": d8}


# ================================================================ Hindi (hand-written, not translated by the LLM)
def _facts_hi(s, source):
    key = s["cause"] or s["hint"]
    K = text("hi", key)
    st = _stratum(s, key) if key else None
    pc = s["pchart"]
    outs = [w for w in pc if w["out"]]

    d2 = [f"{fmt.clock(s['from'])} से {fmt.clock(s['to'])} ({s['minutes']} मिनट) के बीच NAZAR ने {s['n']} वॉशर जाँचे: "
          f"{s['reject']} रिजेक्ट हुए और {s['hold']} जाँच के लिए होल्ड पर रखे गए, यानी {fmt.pct(s['rate'])}% वॉशर "
          f"फ्लैग हुए।"]
    if outs:
        d2.append(f"फ्लैग दर {len(pc)} में से {len(outs)} समय-खंडों में 3-सिग्मा नियंत्रण सीमा से ऊपर गई, पहली बार "
                  f"{fmt.clock(outs[0]['from'])} से शुरू होने वाले खंड में।")
    else:
        d2.append(f"फ्लैग दर सभी {len(pc)} समय-खंडों में 3-सिग्मा नियंत्रण सीमा के अंदर रही।")
    if st:
        d2.append(f"जब {K['state']} ({_amber(st)}), तब {fmt.pct(st['high_rate'])}% वॉशर फ्लैग हुए ({st['high_n']} में "
                  f"से {st['high_bad']}); बाकी समय {fmt.pct(st['low_rate'])}% ({st['low_n']} में से {st['low_bad']})।")

    head = f"अब तक गेट ने {s['reject']} वॉशर हटाए और {s['hold']} वॉशर हाथ से जाँच के लिए होल्ड पर रखे गए। "
    d3 = head + (text("hi", s["cause"])["contain"] if not s["hint"] else
                 "कारण पक्का होने तक हर वॉशर कैमरे से गुज़रता रहे और होल्ड वाले वॉशर हाथ से जाँचे जाएँ।")

    others = [x for x in s["strata"] if x["testable"] and x["factor"] != key]
    other_txt = "; ".join(f"{text('hi', x['factor'])['label']}: पीली स्थिति में {fmt.pct(x['high_rate'])}%, बाकी समय "
                          f"{fmt.pct(x['low_rate'])}%" for x in others)
    if s["cause"]:
        d4 = (f"{K['cause']} सबूत: जब {K['state']}, तब {fmt.pct(st['high_rate'])}% वॉशर फ्लैग हुए; बाकी समय "
              f"{fmt.pct(st['low_rate'])}%, यानी {fmt.ratio(st['ratio'])} गुना (Fisher's exact test, "
              f"{fmt.pval(st['p_value'])})।")
        if other_txt:
            d4 += f" बाकी सेंसरों से कोई साफ़ संबंध नहीं मिला ({other_txt})।"
        d4 += _untested(s, key, "hi")
    elif s["hint"]:
        d4 = (f"अभी साबित नहीं। डेटा {K['fault']} की ओर इशारा करता है: जब {K['state']}, तब {fmt.pct(st['high_rate'])}% "
              f"वॉशर फ्लैग हुए, बाकी समय {fmt.pct(st['low_rate'])}% ({fmt.ratio(st['ratio'])} गुना), पर {s['n']} "
              f"वॉशर में यह संयोग भी हो सकता है ({fmt.pval(st['p_value'])})। लाइन चलाते रहें और ज़्यादा वॉशर के बाद "
              f"एजेंट फिर चलाएँ।")
    else:
        all_txt = "; ".join(f"{text('hi', x['factor'])['label']}: पीली स्थिति में {fmt.pct(x['high_rate'])}%, बाकी "
                            f"समय {fmt.pct(x['low_rate'])}% ({fmt.pval(x['p_value'])})"
                            for x in s["strata"] if x["testable"])
        d4 = K["cause"] + (f" {s['n']} वॉशर का सबूत: {all_txt}।" if all_txt else
                           f" किसी भी पीली स्थिति में तुलना के लिए पर्याप्त वॉशर नहीं थे (हर तरफ़ कम से कम "
                           f"{MIN_GROUP} चाहिए)।")
        d4 += _untested(s, None, "hi") if all_txt else ""

    title = K["title"] if not s["hint"] else f"संभावित कारण: {K['label']} (अभी साबित नहीं)"
    summary = f"{s['n']} वॉशर जाँचे गए, {s['bad']} फ्लैग हुए ({fmt.pct(s['rate'])}%)।"
    if s["cause"]:
        summary += (f" जब {K['state']}, तब वॉशर {fmt.ratio(st['ratio'])} गुना ज़्यादा फ्लैग हुए "
                    f"({fmt.pval(st['p_value'])})। सबसे संभावित कारण: {K['fault']}।")
    elif s["hint"]:
        summary += f" {K['label']} से संबंध हो सकता है, अभी साबित नहीं।"
    else:
        summary += " कोई भी मशीन स्थिति रिजेक्ट की वजह नहीं बताती।"
    ba = s.get("before_after")
    if ba and ba["verdict"] not in ("wait", "no-before"):
        summary += f" सुधार के बाद फ्लैग दर {fmt.pct(ba['before_rate'])}% से {fmt.pct(ba['after_rate'])}% हुई।"
    d1 = ("टीम परख: लाइन ऑपरेटर (बेल्ट चलाता है और अलार्म पर कार्रवाई करता है), मेंटेनेंस (मशीन और बिजली की "
          "मरम्मत) और क्वालिटी (NAZAR जाँच स्टेशन, इस रिपोर्ट के ज़िम्मेदार)। "
          f"डेटा: NAZAR जाँच लॉग ({source})।")
    return {"title": title, "summary": summary, "D1": d1, "D2": " ".join(d2), "D3": d3, "D4": d4, "D6": _d6_hi(s)}


def _d6_hi(s):
    ba = s.get("before_after")
    key = s["cause"] or s["hint"]
    label = text("hi", key)["label"] if key else "मशीन स्थिति"
    if not ba:
        return ("अभी बाकी है। सुधार के बाद कंसोल में सुधार का समय दर्ज करें, और वॉशर चलाएँ और यह रिपोर्ट फिर बनाएँ: "
                f"NAZAR सुधार से पहले और बाद की फ्लैग दर और {label} की तुलना करेगा।")
    out = f"सुधार {fmt.clock(ba['fix_at'])} पर दर्ज हुआ" + (f": {ba['fix_note']}।" if ba["fix_note"] else "।")
    if ba["before_n"] and ba["after_n"]:
        if ba["cause_before"] is not None:
            out += (f" सुधार से पहले {fmt.pct(ba['cause_before'])}% वॉशर {label} की पीली स्थिति में जाँचे गए; "
                    f"सुधार के बाद {fmt.pct(ba['cause_after'])}%।")
        out += (f" फ्लैग वॉशर: पहले {ba['before_n']} में से {ba['before_bad']} ({fmt.pct(ba['before_rate'])}%), "
                f"बाद में {ba['after_n']} में से {ba['after_bad']} ({fmt.pct(ba['after_rate'])}%)।")
    out += {
        "no-before": " सुधार से पहले कोई वॉशर नहीं जाँचा गया, इसलिए तुलना नहीं हो सकती।",
        "wait": f" फैसला अभी जल्दी है: सुधार के बाद कम से कम {MIN_AFTER} वॉशर चाहिए (अभी {ba['after_n']})।",
        "worked": f" फ्लैग दर साफ़ तौर पर घटी (Fisher's exact test, {fmt.pval(ba['p_rate'])}): सुधार काम कर गया।",
        "cause-removed": f" कारण वाली स्थिति साफ़ तौर पर खत्म हुई ({fmt.pval(ba['p_cause'])}) और फ्लैग दर कम है, पर "
                         f"अभी पक्का साबित नहीं ({fmt.pval(ba['p_rate'])}): सुधार असरदार दिखता है, नज़र रखें।",
        "worse": f" सुधार के बाद फ्लैग दर बढ़ गई ({fmt.pval(ba['p_rate'])}): सुधार ने कारण को नहीं हटाया, फिर से जाँचें।",
        "unclear": f" अभी कोई साफ़ बदलाव नहीं ({fmt.pval(ba['p_rate'])})। नज़र रखें, या कोई दूसरा कारण खोजें।",
    }[ba["verdict"]]
    return out


def _explain_hi(s):
    key = s["cause"] or s["hint"]
    K = text("hi", key)
    v = _verdict_key(s)
    if s["hint"]:
        d8 = "अभी बंद न करें: और वॉशर चलाएँ और कारण पक्का करने के लिए रिपोर्ट फिर बनाएँ।"
    elif not s["cause"]:
        d8 = "बैच जाँच से खराबी का स्रोत पक्का होने के बाद ही यह 8D बंद करें; फिर सीख दर्ज करें और टीम को धन्यवाद दें।"
    elif v == "worked":
        d8 = ("8D बंद करें: डेटा दिखाता है कि सुधार काम कर गया। सुधार को मेंटेनेंस लॉग में लिखें, नई जाँचों को शिफ्ट "
              "चेकलिस्ट में जोड़ें और ऑपरेटर, मेंटेनेंस और क्वालिटी टीम को धन्यवाद दें।")
    elif v == "cause-removed":
        d8 = "कम दर पक्की करने के लिए 8D एक और शिफ्ट खुला रखें, फिर बंद करें, सुधार दर्ज करें और टीम को धन्यवाद दें।"
    else:
        d8 = ("8D खुला रखें। सुधार के बाद पूरी शिफ्ट तक फ्लैग दर नियंत्रण सीमा के अंदर रहे, तब इसे बंद करें, सीख दर्ज "
              "करें और टीम को धन्यवाद दें।")
    d5 = ("पहले जाँचें, फिर करें। " + K["act"]) if s["hint"] else K["act"]
    return {"why": list(K["why"]), "D5": d5, "D7": K["prevent"], "D8": d8}


# ================================================================ public
def draft(s, lang, source="live"):
    """The full template 8D: {title, summary, D1..D8 except D5/D7/D8 text keys, why[5], D5, D7, D8}."""
    src = _source(source)
    if lang == "hi":
        return {**_facts_hi(s, src), **_explain_hi(s)}
    return {**_facts_en(s, src), **_explain_en(s)}


def explain_get(d, tag):
    return d["why"][int(tag[3]) - 1] if tag.startswith("WHY") else d[tag]


def sections(d, lang, by=None):
    """Contract shape: [{id, title, body}], plus `by` (who wrote it) and the 5-Why list on D4."""
    by = by or {}
    titles = SECTION_TITLES["hi" if lang == "hi" else "en"]
    why_head = "पाँच बार क्यों (5-Why):" if lang == "hi" else "5-Why:"
    out = []
    for i in range(1, 9):
        sid = f"D{i}"
        body = d[sid]
        writer = by.get(sid, "template")
        sec = {"id": sid, "title": titles[sid]}
        if sid == "D4":
            whys = d["why"]
            body = body + "\n\n" + why_head + "\n" + "\n".join(f"{k + 1}. {w}" for k, w in enumerate(whys))
            why_by = [by.get(f"WHY{k}", "template") for k in range(1, 6)]
            writer = "template" if all(w == "template" for w in why_by) else "template+llm"
            sec["why"] = list(whys)
            sec["why_by"] = why_by
        sec["body"] = body
        sec["by"] = writer
        out.append(sec)
    return out
