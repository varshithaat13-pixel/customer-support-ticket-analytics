"""Human-readable scorecard and trace rendering."""

from __future__ import annotations

from .schemas import TicketScore


def render_scorecard(
    manual: list[TicketScore],
    automated: list[TicketScore] | None = None,
) -> str:
    lines = [
        "",
        "EVALUATION SCORECARD",
        "=" * 78,
        "",
        f"{'id':<4}{'gate':>7}{'cov':>7}{'faith':>8}{'prec':>6}{'rec':>6}{'spec':>6}{'wtd':>8}  verdict",
        "-" * 78,
    ]
    for s in manual:
        lines.append(
            f"{s.ticket_id:<4}{s.gate:>7}{s.coverage:>7.3f}{s.faithfulness:>8.3f}"
            f"{s.precision:>6.1f}{s.recall:>6.1f}{s.specificity:>6.1f}"
            f"{s.weighted_total:>8.3f}  {s.verdict}"
        )

    if automated:
        lines += ["", "LLM-AS-JUDGE (automated)", "-" * 78]
        for s in automated:
            lines.append(
                f"{s.ticket_id:<4}{s.gate:>7}{s.coverage:>7.3f}{s.faithfulness:>8.3f}"
                f"{s.precision:>6.1f}{s.recall:>6.1f}{s.specificity:>6.1f}"
                f"{s.weighted_total:>8.3f}  {s.verdict}"
            )

    lines += ["", ""]
    return "\n".join(lines)


def render_trace(manual: list[TicketScore]) -> str:
    lines = ["", "MANUAL TRACE (golden set)", "=" * 78]
    for s in manual:
        lines += [
            "",
            f"Ticket {s.ticket_id}",
            f"  gate        : {s.gate}",
            f"  coverage    : {s.coverage}",
            f"  faithfulness: {s.faithfulness}",
            f"  precision   : {s.precision}",
            f"  recall      : {s.recall}",
            f"  specificity : {s.specificity}",
            f"  weighted    : {s.weighted_total}",
            f"  dimensions  : {s.dimensions}",
            f"  verdict     : {s.verdict}",
            f"  reason      : {s.reason}",
        ]
    return "\n".join(lines)
