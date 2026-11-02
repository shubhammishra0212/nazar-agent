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
- Unit tests (`tests/test_agent.py`): 13 tests pass (`python3 -m unittest discover -s tests`).
- `run.sh`, `Start Agent.command`.

## Verified
- Stats on demo logs: loose-mount -> cause vib (ratio 9.1, p < 0.001), fix verdict "worked"
  (flagged 16% -> 3.7%, shaking share 44% -> 2.5%); no-cause -> no cause (1 false alarm in 40 seeds);
  dim-light -> lux; 12 rows -> enough:false.
- HTTP: /health, OPTIONS (CORS), bad JSON / empty body / unknown path / non-list inspections -> ok:false.
- `/report` use_llm:false EN and HI: ~1 ms.
- LLM English (before power cut): cold 28.1 s (load 7.5 s + generate 20.6 s), warm 19.7 s, 309 tokens,
  8/8 sections passed the checks.

## In progress
- LLM Hindi run (after restart).

## Next
- README.md, docs/agent.md + PDF (docs/NAZAR-03-Root-Cause-Agent.pdf, copy to ../PDFs/).
