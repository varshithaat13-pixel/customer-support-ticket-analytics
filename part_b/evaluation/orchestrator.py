"""Top-level orchestration.

Runs the manual golden-set benchmark, then the LLM-as-judge layer on the same
tickets, then calibrates the two. This is the single entry point for the
evaluation pipeline.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .schemas import TicketScore
from .manual import run_manual, GOLDEN_PATH
from .llm_judge import score_llm
from .calibrate import calibrate
from .report import render_scorecard, render_trace


def _dump(model: TicketScore) -> dict:
    if hasattr(model, "model_dump"):
        return model.model_dump()  # type: ignore[attr-defined]
    return model.dict()  # type: ignore[no-any-return]


def run(
    golden_path: str | Path = GOLDEN_PATH,
    use_llm: bool = True,
    output_path: str | Path | None = None,
) -> dict[str, Any]:
    """Execute the full orchestration and return a serialisable report."""

    # Step 1: Manual golden set — the score of record.
    manual_scores = run_manual(golden_path)

    # Step 2: LLM-as-judge on the same tickets (automated layer).
    automated_scores: list[TicketScore] = []
    if use_llm:
        payload = json.loads(Path(golden_path).read_text(encoding="utf-8"))
        for case in payload["cases"]:
            automated_scores.append(
                score_llm(case["reference"], case["summary"], case["id"])
            )

    # Step 3: Calibration — does the automated layer agree with the manual one?
    calibration = calibrate(manual_scores, automated_scores) if automated_scores else {}

    # Step 4: Render reports.
    scorecard = render_scorecard(
        manual_scores, automated_scores if automated_scores else None
    )
    trace = render_trace(manual_scores)

    report: dict[str, Any] = {
        "manual": [_dump(s) for s in manual_scores],
        "automated": [_dump(s) for s in automated_scores],
        "calibration": calibration,
        "scorecard": scorecard,
        "trace": trace,
    }

    if output_path:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path).write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(scorecard)
    print(trace)
    if calibration:
        print("\nCALIBRATION")
        print("-" * 78)
        for key, value in calibration.items():
            print(f"  {key}: {value}")
    else:
        print("\nCALIBRATION: skipped (no automated scores available)")

    return report


if __name__ == "__main__":
    run(use_llm=True)
