"""Deterministic manual (golden-set) scorer.

This is the score of record. A human labels each fact slot as kept/lost and
flags any invented claims. This module only counts, divides, and derives a
1-5 rubric mechanically — it never reads English or calls a model.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .schemas import TicketScore

GOLDEN_PATH = Path(__file__).resolve().parent / "data" / "golden_set.json"


def load_golden_set(path: str | Path = GOLDEN_PATH) -> list[dict[str, Any]]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return payload["cases"]


def score_case(case: dict[str, Any]) -> TicketScore:
    """Derive a TicketScore mechanically from human labels in golden_set.json."""
    ticket_id = case["id"]
    human: dict[str, bool] = case["human"]
    invented: list[str] = case.get("invented", [])

    kept = sum(1 for v in human.values() if v)
    total_facts = len(human)
    coverage = kept / total_facts if total_facts else 0.0

    true_claims = kept
    all_claims = kept + len(invented)
    faithfulness = true_claims / all_claims if all_claims else 1.0

    # Knockout gate: product must be named.
    gate = "PASS" if human.get("product", False) else "FAIL"

    # Derived 1-5 rubric — every number traces back to a human boolean above.
    entity_grounding = 5 if human.get("product", False) else 1
    completeness = 1 + int(4 * coverage)
    faithfulness_5 = 3 if invented else 5
    actionability = 2 if not human.get("product", False) else 4

    dimensions = {
        "entity_grounding": float(entity_grounding),
        "completeness": float(completeness),
        "faithfulness_5": float(faithfulness_5),
        "actionability": float(actionability),
    }

    # Map onto the shared 3-dimension schema.
    precision = float(entity_grounding)
    recall = float(completeness)
    specificity = float(faithfulness_5)

    weighted_total = TicketScore.compute_weighted(precision, recall, specificity)

    # Verdict / reason.
    if gate == "FAIL":
        verdict = "FAIL"
        reason = "Product not named — definitionally unactionable"
    elif invented:
        verdict = "PASS with invention"
        reason = f"Invented claim(s): {', '.join(invented)}"
    elif coverage < 1.0:
        verdict = "PASS - incomplete"
        reason = f"Dropped {total_facts - kept} of {total_facts} reference facts"
    else:
        verdict = "PASS"
        reason = "All reference facts kept, nothing invented"

    return TicketScore(
        ticket_id=ticket_id,
        gate=gate,
        coverage=round(coverage, 4),
        faithfulness=round(faithfulness, 4),
        precision=precision,
        recall=recall,
        specificity=specificity,
        weighted_total=weighted_total,
        dimensions=dimensions,
        verdict=verdict,
        reason=reason,
    )


def run_manual(path: str | Path = GOLDEN_PATH) -> list[TicketScore]:
    cases = load_golden_set(path)
    return [score_case(c) for c in cases]
