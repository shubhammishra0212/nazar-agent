"""Tests for statistics, templates and the LLM checker (no model needed).

    python -m unittest discover -s tests -v
"""
import json
import math
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [ROOT, os.path.join(ROOT, "tools")]

import make_demo_log as demo  # noqa: E402
from nazar_agent import engine, llm, stats  # noqa: E402
from nazar_agent.report import FACT_KEYS  # noqa: E402


def brute_fisher(a, b, c, d):
    """Fisher exact by exact integer arithmetic, to check the log-space version."""
    r1, r2, c1, n = a + b, c + d, a + c, a + b + c + d
    prob = lambda x: math.comb(r1, x) * math.comb(r2, c1 - x) / math.comb(n, c1)  # noqa: E731
    p0 = prob(a)
    return sum(prob(x) for x in range(max(0, c1 - r2), min(c1, r1) + 1) if prob(x) <= p0 * (1 + 1e-7))


class Fisher(unittest.TestCase):
    def test_known_values(self):
        self.assertAlmostEqual(stats.fisher_exact(3, 1, 1, 3), 0.4857, places=4)     # tea-tasting example
        self.assertAlmostEqual(stats.fisher_exact(1, 9, 11, 3), 0.002759, places=5)  # textbook example
        self.assertEqual(stats.fisher_exact(0, 0, 5, 5), 1.0)

    def test_matches_brute_force(self):
        for t in [(10, 20, 4, 86), (31, 67, 7, 195), (2, 23, 24, 191), (0, 30, 12, 50), (5, 5, 5, 5)]:
            self.assertAlmostEqual(stats.fisher_exact(*t), brute_fisher(*t), places=9, msg=str(t))


class Stories(unittest.TestCase):
    def test_loose_mount_finds_vibration(self):
        for seed in (42, 1, 2, 3, 4):
            s, ok = stats.analyse(demo.make("loose-mount", seed))
            self.assertTrue(ok)
            self.assertEqual(s["cause"], "vib", f"seed {seed}")
            vib = next(x for x in s["strata"] if x["factor"] == "vib")
            self.assertGreater(vib["ratio"], 3)
            self.assertLess(vib["p_value"], 0.001)
            ba = s["before_after"]
            self.assertLess(ba["after_rate"], ba["before_rate"])
            self.assertLess(ba["cause_after"], ba["cause_before"] / 4)
            self.assertIn(ba["verdict"], ("worked", "cause-removed"))
            self.assertEqual(s["ignored"], 2)                       # the two NO_PART rows
            self.assertEqual(s["n"], ba["before_n"] + ba["after_n"])

    def test_no_cause_is_honest(self):
        false_alarms = 0
        for seed in range(1, 21):
            s, ok = stats.analyse(demo.make("no-cause", seed))
            self.assertTrue(ok)
            false_alarms += s["cause"] is not None
        self.assertLessEqual(false_alarms, 1)
        out = engine.build(demo.make("no-cause", 42, use_llm=False))
        self.assertIsNone(out["stats"]["cause"])
        self.assertTrue(out["report"]["title"].startswith("No machine cause"))

    def test_dim_light_is_below_amber(self):
        s, _ = stats.analyse(demo.make("dim-light", 42))
        self.assertEqual(s["cause"], "lux")
        lux = next(x for x in s["strata"] if x["factor"] == "lux")
        self.assertGreater(lux["high_rate"], lux["low_rate"])

    def test_too_few_rows(self):
        out = engine.build(demo.make("few", 42, use_llm=False))
        self.assertTrue(out["ok"])
        self.assertFalse(out["enough"])
        self.assertIn("message", out)
        self.assertNotIn("report", out)
        self.assertEqual(out["stats"]["n"], 12)


class Report(unittest.TestCase):
    def test_contract_shape(self):
        out = engine.build(demo.make("loose-mount", 42, use_llm=False))
        self.assertEqual(out["writer"], "template")
        s = out["stats"]
        for k in ("n", "bad", "rate", "pchart", "strata", "cause", "before_after"):
            self.assertIn(k, s)
        for k in ("from", "to", "n", "bad", "p", "ucl", "lcl"):
            self.assertIn(k, s["pchart"][0])
        for k in ("factor", "label", "high_n", "high_bad", "low_n", "low_bad", "ratio", "p_value"):
            self.assertIn(k, s["strata"][0])
        for k in ("before_n", "before_bad", "after_n", "after_bad", "cause_before", "cause_after"):
            self.assertIn(k, s["before_after"])
        self.assertEqual([x["id"] for x in out["report"]["sections"]], [f"D{i}" for i in range(1, 9)])
        json.dumps(out, allow_nan=False)                           # strict JSON

    def test_hindi_has_same_numbers(self):
        req = demo.make("loose-mount", 42, use_llm=False)
        en = engine.build(dict(req, lang="en"))["report"]["sections"]
        hi = engine.build(dict(req, lang="hi"))["report"]["sections"]
        for a, b in zip(en, hi):
            if a["id"] in ("D2", "D6"):
                self.assertEqual(llm.numbers(a["body"]), llm.numbers(b["body"]), a["id"])
            self.assertGreater(sum("ऀ" <= c <= "ॿ" for c in b["body"]), 20, b["id"])

    def test_bad_input_never_crashes(self):
        for bad in [None, [], "x", {}, {"inspections": "no"}, {"inspections": [1, None, {"verdict": "PASS"}]},
                    {"inspections": [{"at": "x", "verdict": "REJECT", "vib": "nan"}] * 30},
                    {"inspections": [{"at": i, "verdict": "PASS", "vib": float("inf")} for i in range(30)],
                     "limits": "nope", "fix_at": "soon"}]:
            out = engine.build(bad)
            self.assertIn("ok", out)
            json.dumps(out, allow_nan=False)


class Checker(unittest.TestCase):
    def setUp(self):
        s, _ = stats.analyse(demo.make("loose-mount", 42))
        from nazar_agent import report
        self.en = report.draft(s, "en")
        self.allowed = llm.allowed_numbers(self.en)

    def test_numbers_normalise(self):
        self.assertEqual(llm.numbers("0.080 g at 09:05, ३२% and 7.50x"), {"0.08", "9:05", "32", "7.5"})

    def test_invented_number_is_rejected(self):
        self.assertIsNone(llm.check("D5", "Maintenance tightens the motor mount screws.", "en", self.allowed))
        self.assertIn("invented", llm.check("D5", "Tighten the 4 screws to 12 Nm.", "en", self.allowed))

    def test_blame_and_language(self):
        self.assertIsNotNone(llm.check("WHY2", "The reject gate malfunctioned during the run.", "en", self.allowed))
        self.assertEqual(llm.check("D7", "Check the mount every shift and act on alarms.", "hi", self.allowed),
                         "not Hindi")
        self.assertIsNone(llm.check("D7", "हर शिफ्ट मोटर माउंट के पेंच जाँचें और अलार्म पर तुरंत कार्रवाई करें।", "hi",
                                    self.allowed))

    def test_loops_and_why_form(self):
        self.assertEqual(llm.check("D8", "Close the 8D 8D report now. All good.", "en", self.allowed), "repeats itself")
        self.assertEqual(llm.check("D8", "सुधार काम कर गया। टीम को धन्यवाद दें। सुधार काम कर गया।", "hi", self.allowed),
                         "repeats itself")
        self.assertIsNotNone(llm.check("WHY1", "क्या ज़्यादा वॉशर रिजेक्ट हुए? क्योंकि मोटर हिल रही थी।", "hi",
                                       self.allowed))
        self.assertIsNone(llm.check("WHY1", "ज़्यादा वॉशर रिजेक्ट क्यों हुए? क्योंकि मोटर हिल रही थी।", "hi",
                                    self.allowed))
        self.assertIsNone(llm.check("WHY3", "Why is the motor shaking? Its mount has worked loose.", "en", self.allowed))
        self.assertIsNotNone(llm.check("WHY3", "The motor shakes because its mount is loose.", "en", self.allowed))

    def test_echoed_instruction_is_stripped(self):
        got = llm.parse("[D7] How to stop it coming back? Add the mount to the checklist.\n[WHY1] Why? Because.")
        self.assertEqual(got["D7"], "Add the mount to the checklist.")
        self.assertEqual(got["WHY1"], "Why? Because.")

    def test_parse_tags(self):
        got = llm.parse("**[WHY1]** First.\n[WHY2]: Second one\nD5: Do it.\n[D8] Close.")
        self.assertEqual(got, {"WHY1": "First.", "WHY2": "Second one", "D5": "Do it.", "D8": "Close."})


if __name__ == "__main__":
    unittest.main()
