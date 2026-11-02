"""One request in, one response out: statistics -> template 8D -> (optional) LLM explanations."""
import time

from . import llm, report, stats
from .knowledge import text

MIN_LLM_SECTIONS = 4     # fewer checked LLM sections than this: the template is cleaner than a patchwork


def _flag(v, default=True):
    if v is None:
        return default
    if isinstance(v, str):
        return v.strip().lower() not in ("false", "0", "no", "off", "")
    return bool(v)


def build(req):
    t0 = time.time()
    if not isinstance(req, dict):
        return {"ok": False, "error": "body must be a JSON object (contract section 5)"}
    if not isinstance(req.get("inspections"), list):
        return {"ok": False, "error": "'inspections' must be a list of inspection rows"}
    lang = "hi" if str(req.get("lang") or "en").lower().startswith("hi") else "en"
    use_llm = _flag(req.get("use_llm"), True)

    s, enough = stats.analyse(req)
    for st in s.get("strata", []):
        st["label"] = text(lang, st["factor"])["label"]

    def done(out):
        out["ms"] = round((time.time() - t0) * 1000)
        return out

    if not enough:
        more = stats.MIN_ROWS - s["n"]
        msg = (f"केवल {s['n']} वॉशर जाँचे गए हैं। रिपोर्ट के लिए कम से कम {stats.MIN_ROWS} चाहिए ({more} और)।"
               if lang == "hi" else
               f"Only {s['n']} washers inspected. A report needs at least {stats.MIN_ROWS} ({more} more).")
        return done({"ok": True, "enough": False, "writer": "template", "lang": lang, "stats": s, "message": msg})

    source = req.get("source") or "live"
    d_en = report.draft(s, "en", source)
    d_out = d_en if lang == "en" else report.draft(s, "hi", source)
    by, writer, llm_info = {}, "template", None

    if not use_llm:
        note = "Template only (use_llm is false)."
    else:
        res, why = llm.rewrite(d_en, d_out, lang)
        if res is None:
            note = f"Template used: {why}."
        else:
            good = [t for t, w in res["by"].items() if w == "llm"]
            llm_info = {"model": llm.NAME, "gen_s": res["gen_s"], "tokens": res["tokens"], "cut": res["cut"],
                        "load_s": res["load_s"], "accepted": good, "rejected": res["rejected"]}
            if len(good) >= MIN_LLM_SECTIONS:
                d_out = dict(d_out, why=list(d_out["why"]))
                for tag, body in res["text"].items():
                    if tag.startswith("WHY"):
                        d_out["why"][int(tag[3]) - 1] = body
                    else:
                        d_out[tag] = body
                by = res["by"]
                writer = "llm"
                note = (f"Facts and numbers: NAZAR statistics templates. Explanations: local LLM "
                        f"({len(good)} of {len(res['by'])} sections passed the checks"
                        + (f"; {len(res['rejected'])} kept the template text)." if res["rejected"] else ")."))
            else:
                note = (f"Template used: only {len(good)} of {len(res['by'])} LLM sections passed the checks "
                        f"(numbers, blame, language).")

    rep = {"title": d_out["title"], "summary": d_out["summary"], "sections": report.sections(d_out, lang, by)}
    return done({"ok": True, "enough": True, "writer": writer, "lang": lang, "note": note, "llm": llm_info,
                 "stats": s, "report": rep})
