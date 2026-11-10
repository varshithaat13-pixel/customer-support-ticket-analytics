"""Shared evaluation contract.

Both the manual golden-set scorer and the LLM-as-judge scorer return the same
TicketScore shape, so they can be compared directly and swapped cleanly.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

# Must sum to 1.0. Enforced here (not just by a comment).
WEIGHTS = {
    "precision": 0.35,
    "recall": 0.40,
    "specificity": 0.25,
}


class TicketScore(BaseModel):
    """Single ticket evaluation result."""

    ticket_id: str
    gate: Literal["PASS", "FAIL"]
    coverage: float = Field(
        ge=0.0, le=1.0, description="facts kept / total reference facts"
    )
    faithfulness: float = Field(
        ge=0.0, le=1.0, description="true claims / all claims"
    )
    precision: float = Field(ge=0.0, le=5.0)
    recall: float = Field(ge=0.0, le=5.0)
    specificity: float = Field(ge=0.0, le=5.0)
    weighted_total: float = Field(ge=0.0, le=1.0)
    dimensions: dict[str, float] = Field(default_factory=dict)
    verdict: str
    reason: str

    @classmethod
    def compute_weighted(
        cls, precision: float, recall: float, specificity: float
    ) -> float:
        """Normalised 0.0–1.0 weighted total using the shared rubric weights."""
        total = (
            precision * WEIGHTS["precision"]
            + recall * WEIGHTS["recall"]
            + specificity * WEIGHTS["specificity"]
        ) / 5.0
        return round(total, 4)

    def model_dump_compat(self) -> dict:
        """Pydantic v1/v2 compatible serialisation."""
        if hasattr(self, "model_dump"):
            return self.model_dump()  # type: ignore[attr-defined]
        return self.dict()  # type: ignore[no-any-return]
