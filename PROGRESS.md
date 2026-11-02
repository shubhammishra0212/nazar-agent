# nazar-agent progress

After any restart: read this file and `git log` first.

## Done
- Statistics core (`nazar_agent/stats.py`): p-chart (windows of 20, 3-sigma), stratification vib/lux/temp/ma
  against amber (lux = below amber), rate ratio + own two-sided Fisher exact test, Bonferroni, cause/hint,
  before/after (defect rate AND cause-state share) around `fix_at`.
- Line knowledge EN + HI (`knowledge.py`), 8D templates EN + HI (`report.py`).
- LLM worker (`llm.py`): MLX load + generate on one thread, wall-clock budget, number/blame/language checks.
- Engine + HTTP service on 127.0.0.1:8766 (`engine.py`, `service.py`), contract section 5.
- Demo log generator (`tools/make_demo_log.py`): loose-mount, no-cause, dim-light, few.
- Unit tests (`tests/test_agent.py`): 16 tests pass (`python3 -m unittest discover -s tests`).
- `run.sh`, `Start Agent.command`.

## Verified
- Stats on demo logs: loose-mount -> cause vib (ratio 9.1, p < 0.001), fix verdict "worked"
  (flagged 16% -> 3.7%, shaking share 44% -> 2.5%); no-cause -> no cause (1 false alarm in 40 seeds);
  dim-light -> lux; 12 rows -> enough:false.
- HTTP: /health, OPTIONS (CORS), bad JSON / empty body / unknown path / non-list inspections -> ok:false.
- `/report` use_llm:false EN and HI: ~1 ms.
- LLM English (final code, after power cut; request without `lang` -> defaults to en):
  loose-mount cold 27.0 s (load 6.9 s + write 20.1 s, 320 tokens), warm 19.7-20.2 s, 8/8 sections passed;
  no-cause warm 15.1 s, 7/8 passed (WHY3 failed the why-question check -> template text kept).
  Same input gives the same text (fixed seed). All numbers in LLM text are checked against the facts.
- Service stopped after tests; port 8766 free.
- README.md written.
- docs/agent.md + docs/NAZAR-03-Root-Cause-Agent.pdf (7 pages, all pages checked as PNG), copied to
  ../PDFs/. No Devanagari in the PDF.
- D4 now names a second significant sensor ("Also linked") instead of calling it unlinked (unit-tested).

## Scope change (coordinator, 2 Nov)
- 8D report is ENGLISH ONLY for now. Hindi = planned / template only, not shown in the demo.
  Hindi templates exist and are unit-tested without the LLM. One Hindi LLM run was made before the scope
  change (44 s, 702 tokens; found a looping D8 and a broken WHY1 -> added repeat + why-form checks). No more
  Hindi work.

## Known limits (not verified)
- Checks catch invented numbers, blame, loops and broken 5-Why form, not meaning drift: in the no-cause run
  the LLM's D5 said "maintenance will repair the current batch" and dropped the hand-sample step.
- Not tested against the real console or real line data yet (demo logs only).

## In progress
- Nothing.

## Next
- Test with the real console (POST from the page, CORS from origin null) and a real line log.
