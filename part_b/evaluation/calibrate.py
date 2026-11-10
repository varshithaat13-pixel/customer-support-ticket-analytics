"""Calibration: compare manual golden-set scores against LLM-as-judge scores.

Run this after scoring the same golden tickets both ways. If agreement is
high, you can trust the LLM judge on new (unlabeled) tickets.
"""

from __future__ import annotations

from typing import Any

from .schemas import TicketScore


def calibrate(manual: list[TicketScore], automated: list[TicketScore]) -> dict[str, Any]:
    if len(manual) != len(automated):
        raise ValueError("manual and automated lists must have the same length")

    by_id = {s.ticket_id: s for s in automated}

    total = 0
    gate_agreements = 0
    wt_diffs: list[float] = []
    dim_diffs: dict[str, list[float]] = {
        "precision": [],
        "recall": [],
        "specificity": [],
    }

    for m in manual:
        a = by_id.get(m.ticket_id)
        if a is None:
            continue
        total += 1
        if m.gate == a.gate:
            gate_agreements += 1
        wt_diffs.append(abs(m.weighted_total - a.weighted_total))
        for dim in dim_diffs:
            dim_diffs[dim].append(abs(getattr(m, dim) - getattr(a, dim)))

    def mean(xs: list[float]) -> float:
        return round(sum(xs) / len(xs), 4) if xs else 0.0

    gate_rate = round(gate_agreements / total, 4) if total else 0.0

    return {
        "n_tickets": total,
        "gate_agreement": gate_rate,
        "mean_weighted_total_diff": mean(wt_diffs),
        "mean_dimension_diff": {d: mean(v) for d, v in dim_diffs.items()},
        "calibrated": gate_rate >= 0.8 if total else False,
    }
