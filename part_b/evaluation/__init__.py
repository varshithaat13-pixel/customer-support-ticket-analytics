"""part_b.evaluation

Manual golden-set benchmark + LLM-as-a-judge automated layer.

Usage:
    from part_b.evaluation.orchestrator import run
    report = run()
"""

from .schemas import TicketScore, WEIGHTS
from .manual import run_manual, GOLDEN_PATH, score_case, load_golden_set
from .llm_judge import score_llm, build_prompt
from .calibrate import calibrate


def __getattr__(name: str):
    if name == "run":
        from .orchestrator import run

        return run
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    "TicketScore",
    "WEIGHTS",
    "run_manual",
    "GOLDEN_PATH",
    "score_case",
    "load_golden_set",
    "score_llm",
    "build_prompt",
    "calibrate",
    "run",
]
