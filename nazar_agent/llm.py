"""The local LLM: Llama 3.1 8B Instruct, 4-bit, run by Apple MLX on this Mac. Offline.

The LLM never decides facts. It only rewrites the explanation parts of the template
8D (5-Why chain, D5 corrective action, D7 prevention, D8 closure), and every section it
writes is checked before it is used:

  * every number in it must already be in the facts or the template (no invented numbers),
  * no blame on the camera / AI / gate / sensors ("the gate malfunctioned"),
  * Hindi sections must really be in Devanagari, English ones must not be,
  * sane length.

A section that fails keeps the template text. MLX is not thread-safe across threads: the
model is loaded AND used on one dedicated worker thread; HTTP threads only queue jobs.
"""
import os
import queue
import re
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DIR = os.path.normpath(os.path.join(HERE, "..", "..", "..", "10-AI", "llm", "llama-3.1-8b-instruct-4bit"))
LLM_DIR = os.path.expanduser(os.environ.get("NAZAR_LLM_DIR") or DEFAULT_DIR)
NAME = "Llama 3.1 8B Instruct 4-bit (MLX)"
GEN_BUDGET_S = {"en": 60.0, "hi": 110.0}      # generation stops at this wall-clock time
LOAD_BUDGET_S = 120.0
MAX_TOKENS = {"en": 900, "hi": 2200}
TEMP = 0.3
SEED = 7

_state = {"model": None, "tok": None, "error": None, "loading": False, "load_s": None}
_gate = threading.Lock()       # one report generation at a time; released by the worker when its job ends
_jobs = queue.Queue()
_thread = {"t": None}
_thread_lock = threading.Lock()


# ---------------------------------------------------------------- worker thread
def _loop():
    while True:
        fn, args, box, done, release = _jobs.get()
        try:
            box["result"] = fn(*args)
        except BaseException as e:          # never kill the worker
            box["error"] = f"{type(e).__name__}: {e}"
        finally:
            if release:
                _gate.release()
            done.set()


def _submit(fn, *args, release=False):
    with _thread_lock:
        if _thread["t"] is None or not _thread["t"].is_alive():
            _thread["t"] = threading.Thread(target=_loop, name="nazar-llm", daemon=True)
            _thread["t"].start()
    box, done = {}, threading.Event()
    _jobs.put((fn, args, box, done, release))
    return box, done


# ---------------------------------------------------------------- status
def installed():
    need = ("config.json", "tokenizer.json", "tokenizer_config.json")
    if not os.path.isdir(LLM_DIR) or not all(os.path.isfile(os.path.join(LLM_DIR, f)) for f in need):
        return False
    files = os.listdir(LLM_DIR)
    if any(f.endswith((".incomplete", ".part")) for f in files):
        return False
    return any(f.endswith(".safetensors") for f in files)


def status():
    """'loaded' | 'installed' | 'missing' (contract section 5)."""
    if _state["model"] is not None:
        return "loaded"
    return "installed" if installed() else "missing"


def busy():
    return _gate.locked() or _state["loading"]


def info():
    return {"name": NAME, "dir": LLM_DIR, "status": status(), "busy": busy(), "error": _state["error"],
            "load_s": _state["load_s"]}


# ---------------------------------------------------------------- jobs (run on the worker only)
def _load():
    if _state["model"] is not None:
        return True
    if not installed():
        _state["error"] = "model files not found in " + LLM_DIR
        return False
    _state["loading"] = True
    t0 = time.time()
    try:
        from mlx_lm import load
        _state["model"], _state["tok"] = load(LLM_DIR)
        _state["error"] = None
        _state["load_s"] = round(time.time() - t0, 1)
    except Exception as e:
        _state["error"] = f"load failed: {type(e).__name__}: {e}"
    finally:
        _state["loading"] = False
    return _state["model"] is not None


def _generate(messages, lang):
    if not _load():
        raise RuntimeError(_state["error"] or "model not loaded")
    import mlx.core as mx
    from mlx_lm import stream_generate
    from mlx_lm.sample_utils import make_sampler
    tok = _state["tok"]
    prompt = tok.apply_chat_template(messages, add_generation_prompt=True, tokenize=False)
    mx.random.seed(SEED)
    t0 = time.time()
    deadline = t0 + GEN_BUDGET_S[lang]
    parts, tokens, cut = [], 0, False
    for r in stream_generate(_state["model"], tok, prompt=prompt, max_tokens=MAX_TOKENS[lang],
                             sampler=make_sampler(temp=TEMP, top_p=0.9)):
        parts.append(r.text)
        tokens = r.generation_tokens
        if time.time() > deadline:
            cut = True
            break
    return {"text": "".join(parts), "tokens": tokens, "gen_s": round(time.time() - t0, 1), "cut": cut}


def preload():
    """Start loading the model in the background (the first report is then quick)."""
    if installed() and _state["model"] is None:
        _submit(_load)


# ---------------------------------------------------------------- prompt
GLOSSARY_HI = ("washer = वॉशर, rejected = रिजेक्ट, held = होल्ड, motor = मोटर, motor mount = मोटर माउंट, belt = बेल्ट, "
               "roller = रोलर, screws = पेंच, tighten = कसें, loose = ढीला, shaking/vibration = कंपन, light = रोशनी, "
               "tunnel = टनल, LED strip = LED पट्टी, diffuser = डिफ्यूज़र, current = करंट, temperature = तापमान, "
               "alarm = अलार्म, amber = पीली, limit = सीमा, checklist = चेकलिस्ट, shift = शिफ्ट, operator = ऑपरेटर, "
               "maintenance = मेंटेनेंस, quality = क्वालिटी, camera = कैमरा, fix = सुधार, report = रिपोर्ट, "
               "guides = गाइड, batch = बैच")

SYSTEM = ("You are the quality engineer of the NAZAR washer inspection line in a small Indian factory, helping to write "
          "an 8D problem-solving report. The statistics and the root cause were already worked out from the line's "
          "data and are given to you as FACTS; you only explain them clearly. Rules: do not add any number, "
          "percentage, time or name that is not in the FACTS or the DRAFT (when in doubt, write no number). Do not "
          "invent new causes, faults or parts. The NAZAR camera, AI, reject gate and sensors work correctly; never "
          "blame them. Plain text only: no markdown, no lists, no bullet symbols.")


def build_messages(draft_en, draft_out, lang):
    """FACTS always in English (the model understands them best); DRAFT in the output language."""
    from .report import explain_get
    facts = (f"TITLE: {draft_en['title']}\nSUMMARY: {draft_en['summary']}\nPROBLEM (D2): {draft_en['D2']}\n"
             f"ROOT CAUSE (D4): {draft_en['D4']}\nVERIFICATION (D6): {draft_en['D6']}")
    tags = ["WHY1", "WHY2", "WHY3", "WHY4", "WHY5", "D5", "D7", "D8"]
    draft = "\n".join(f"[{t}] {explain_get(draft_out, t)}" for t in tags)
    if lang == "hi":
        language = ("simple everyday Hindi in Devanagari script, the way a shop-floor supervisor in India speaks. Use "
                    f"these words: {GLOSSARY_HI}. Keep NAZAR, AI, LED and 8D in English letters. Write digits as 0-9")
    else:
        language = "plain, professional English"
    user = (f"FACTS (decided by the data; do not change them):\n{facts}\n\n"
            f"DRAFT sections:\n{draft}\n\n"
            "Rewrite each DRAFT section so that both a line operator and a manager understand it.\n"
            "[WHY1] to [WHY5]: a 5-Why chain from the problem down to the system cause. Each [WHYn] keeps exactly the "
            "meaning of the draft's [WHYn] (do not merge, repeat or shift steps) and is written as a short question "
            "and its answer, like the draft.\n"
            "[D5]: the corrective actions of the draft as concrete steps, saying who does each: maintenance does the "
            "repair, the operator stops the belt and acts on alarms, quality checks the result.\n"
            "[D7]: how to stop it coming back, from the draft.\n"
            "[D8]: how and when to close the report, consistent with VERIFICATION.\n"
            f"Write in {language}. Output exactly these eight tags in this order, each at the start of its own line "
            "followed by its text, and nothing else.")
    return [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}]


# ---------------------------------------------------------------- checking
TAGS = ["WHY1", "WHY2", "WHY3", "WHY4", "WHY5", "D5", "D7", "D8"]
_TAG_RE = re.compile(r"(?mi)^[ \t>*#_-]*\[?\s*(WHY\s?[1-5]|D[578])\s*\]?[*_]*\s*[:.)\-–]?\s*")
_DEV_DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")
_BLAME = re.compile(r"\b(malfunction\w*|bug|glitch|(camera|gate|sensor|sensors|nazar|ai|software|model|system)\s+"
                    r"(is|was|were|are)\s+(faulty|broken|wrong|defective|inaccurate|failing))\b", re.I)


def parse(text):
    """{tag: text} from the model output (first occurrence of each tag wins)."""
    found = {}
    marks = list(_TAG_RE.finditer(text))
    for i, m in enumerate(marks):
        tag = m.group(1).upper().replace(" ", "")
        end = marks[i + 1].start() if i + 1 < len(marks) else len(text)
        body = text[m.end():end]
        body = re.sub(r"[*#`_]+", "", body)
        body = re.sub(r"\s+", " ", body).strip(" -•–")
        if body and tag not in found:
            found[tag] = body
    return found


def numbers(text):
    """Every number in a text, normalised: '0.080' == '0.08', '09:05' == '9:05', Devanagari digits as 0-9."""
    out = set()
    for m in re.findall(r"\d+(?:[.:]\d+)?", text.translate(_DEV_DIGITS)):
        if ":" in m:
            h, mm = m.split(":", 1)
            m = f"{int(h)}:{mm}"
        elif "." in m:
            whole, frac = m.split(".", 1)
            frac = frac.rstrip("0")
            m = str(int(whole)) + ("." + frac if frac else "")
        else:
            m = str(int(m))
        out.add(m)
    return out


def _devanagari_share(text):
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return 0.0
    return sum("ऀ" <= c <= "ॿ" for c in letters) / len(letters)


def check(tag, body, lang, allowed):
    """None if the section can be used, else the reason it cannot."""
    if not body or len(body) < 12:
        return "empty"
    if len(body) > 700:
        return "too long"
    extra = numbers(body) - allowed
    if extra:
        return "invented number(s): " + ", ".join(sorted(extra))
    if _BLAME.search(body):
        return "blames the inspection system"
    share = _devanagari_share(body)
    if lang == "hi" and share < 0.6:
        return "not Hindi"
    if lang == "en" and share > 0:
        return "not English"
    return None


def allowed_numbers(*drafts):
    from .report import FACT_KEYS
    allowed = {str(i) for i in range(1, 9)}
    for d in drafts:
        for k in FACT_KEYS + ["D5", "D7", "D8"]:
            allowed |= numbers(d[k])
        for w in d["why"]:
            allowed |= numbers(w)
    return allowed


# ---------------------------------------------------------------- public
def rewrite(draft_en, draft_out, lang):
    """Model-written explanation sections, checked. Returns (result, None) or (None, reason).

    result = {"text": {tag: str}, "by": {tag: "llm"|"template"}, "rejected": {tag: reason},
              "gen_s", "tokens", "cut", "load_s"}
    """
    if not installed():
        return None, "local model not installed"
    if not _gate.acquire(blocking=False):
        return None, "local model busy with another report"
    try:
        loaded = _state["model"] is not None
        box, done = _submit(_generate, build_messages(draft_en, draft_out, lang), lang, release=True)
    except Exception as e:                  # could not even queue: give the gate back
        _gate.release()
        return None, f"could not start the local model ({e})"
    wait = GEN_BUDGET_S[lang] + 15 + (0 if loaded else LOAD_BUDGET_S)
    if not done.wait(wait):
        return None, f"local model timed out after {wait:.0f} s"
    if "error" in box:
        return None, f"local model failed ({box['error']})"
    out = box["result"]
    got = parse(out["text"])
    allowed = allowed_numbers(draft_en, draft_out)
    from .report import explain_get
    res = {"text": {}, "by": {}, "rejected": {}, "gen_s": out["gen_s"], "tokens": out["tokens"], "cut": out["cut"],
           "load_s": _state["load_s"] if not loaded else None}
    for tag in TAGS:
        body = got.get(tag)
        reason = check(tag, body, lang, allowed) if body else "missing"
        if reason:
            res["text"][tag] = explain_get(draft_out, tag)
            res["by"][tag] = "template"
            res["rejected"][tag] = reason
        else:
            res["text"][tag] = body
            res["by"][tag] = "llm"
    return res, None
