# part_b/evaluation — Manual benchmark + LLM-as-judge

This folder implements a clean two-layer evaluation pipeline:

1. **Manual / golden-set scorer** (`manual.py`) — the immutable score of record.
   A human labels facts as kept/lost and flags invented claims in
   `data/golden_set.json`. This module only counts and divides; it never reads
   English and never calls a model.

2. **LLM-as-a-judge** (`llm_judge.py`) — the automated layer.
   Returns the same `TicketScore` shape so it can be compared directly with the
   manual scorer. It uses a locally running Ollama model; summaries are not sent
   to a hosted LLM API.

3. **Calibration** (`calibrate.py`) — compares manual vs LLM scores on the same
   golden tickets. If agreement is high, trust the LLM judge on new tickets.

4. **Orchestrator** (`orchestrator.py`) — single entry point.

## File layout

```
part_b/evaluation/
├── __init__.py
├── schemas.py          # Shared TicketScore contract + rubric weights
├── manual.py           # Deterministic golden-set scorer
├── llm_judge.py        # Automated LLM-as-judge scorer
├── calibrate.py        # Manual vs LLM comparison
├── report.py           # Markdown scorecard + trace
├── orchestrator.py     # Pipeline entry point
├── data/
│   └── golden_set.json # Human labels — the benchmark
└── README.md
```

## Run the offline benchmark

```bash
python -c "from part_b.evaluation.orchestrator import run; run(use_llm=False)"
```

The module entry point enables local Ollama scoring by default. To run the
orchestrator without Ollama, explicitly pass `use_llm=False` as shown above.
To run automated scoring, install Ollama, download the default model, and
start the Ollama service:

```powershell
ollama pull qwen2.5:3b
python -m part_b.evaluation.orchestrator
```

Set `OLLAMA_MODEL` and `OLLAMA_HOST` in the process environment before starting
Python if you need to override the defaults (`qwen2.5:3b` and
`http://localhost:11434`).

Or import programmatically:

```python
from part_b.evaluation.orchestrator import run

report = run(use_llm=False)     # offline benchmark only
report = run(use_llm=True)      # also scores with local Ollama
report = run(use_llm=False, output_path="scores.json")  # offline and saves JSON
```

## How to scale

| Step | Action |
|------|--------|
| 1 | Keep adding human-labeled cases to `data/golden_set.json`. |
| 2 | Run Ollama locally for automated judging. |
| 3 | Run `python -m part_b.evaluation.orchestrator` — calibration compares model scores to the manual benchmark. |
| 4 | On new unlabeled tickets, use only `llm_judge.score_llm()`. Periodically re-run manual spot-checks for drift detection. |

## Rubric weights (shared)

- Precision: 35%
- Recall: 40%
- Specificity: 25%

These are enforced in `schemas.py`, not left to a comment.
