# nazar-agent

Root-cause agent for NAZAR (Team Parakh, INDUX 5.0). It takes the console's inspection log,
finds **why** washers get rejected (for example "rejects are 9 times higher while the motor
shakes, so the motor mount is loose"), and writes an 8D report. Everything runs offline on
the Mac, with a local LLM.

HTTP API: `127.0.0.1:8766`, exactly as in `../nazar/CONTRACT.md` section 5.

## Run

```bash
./run.sh                 # or double-click "Start Agent.command"
./run.sh --no-preload    # load the LLM on the first report instead of at start
```

- Python: `../../10-AI/.venv/bin/python` (has `mlx-lm`), override with `NAZAR_PY=/path/to/python`.
  Without it, `run.sh` falls back to `python3` and reports use templates only.
- Model: `../../10-AI/llm/llama-3.1-8b-instruct-4bit`, override with `NAZAR_LLM_DIR`.
- Port check: `lsof -i :8766`.

## Try it

```bash
python3 tools/make_demo_log.py --story loose-mount -o demo/loose-mount.json
curl -s http://127.0.0.1:8766/health
curl -s -X POST -H 'Content-Type: application/json' --data @demo/loose-mount.json http://127.0.0.1:8766/report
```

Stories: `loose-mount` (cause = motor shaking, then a fix that works), `no-cause` (random rejects:
the agent says no machine cause), `dim-light` (cause = low tunnel light), `few` (12 rows: `enough:false`).
Add `--no-llm` for `use_llm:false` (template only, about 1 ms).

## How it works

| Module | Job |
|---|---|
| `nazar_agent/stats.py` | p-chart (3-sigma), defect rate split by each sensor's amber state, rate ratio + Fisher exact test (own code), cause, before/after around `fix_at` |
| `nazar_agent/knowledge.py` | what each machine state means on this line and what to do |
| `nazar_agent/report.py` | 8D templates; all facts and numbers come from here |
| `nazar_agent/llm.py` | Llama 3.1 8B 4-bit on Apple MLX, one worker thread; rewrites only the 5-Why, D5, D7, D8 and checks every section (numbers, blame, loops, why-form) |
| `nazar_agent/engine.py` | request -> stats -> template -> optional LLM -> response |
| `nazar_agent/service.py` | standard-library HTTP server, CORS, never crashes |

Request and response shapes: see CONTRACT.md section 5. Extra response fields: `note`
(who wrote what), `llm` (timings, accepted/rejected sections), per-section `by`, and the
5-Why list on D4.

## Language

The report is **English**. `lang` defaults to `"en"`. Hindi is planned / template only, not
shown in the demo: the Hindi fact templates exist and are unit-tested without the LLM, but the
Hindi LLM path is not part of the demo.

## Tests

```bash
python3 -m unittest discover -s tests -v
```

Measured on the M4 Mac (English, demo log of 300 washers): first report after start
27 s (6.9 s model load + 20 s writing), later reports about 20 s, `use_llm:false` about 1 ms.

Explainer for the team: `docs/NAZAR-03-Root-Cause-Agent.pdf`. Status: `PROGRESS.md`.

Model: Meta Llama 3.1 8B Instruct (Llama 3.1 Community License, "Built with Llama"), MLX 4-bit
conversion by mlx-community.
