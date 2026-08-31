"""Learning subsystem: evidence-based mission evaluation."""
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Evaluation:
    success: bool
    score: float
    lesson: str


class Evaluator:
    """Turns verified results into reusable lessons; never edits other organs."""

    def evaluate(self, expected: dict[str, Any], observed: dict[str, Any]) -> Evaluation:
        if not expected:
            return Evaluation(True, 1.0, "No explicit acceptance criteria supplied.")
        matches = sum(1 for key, value in expected.items() if observed.get(key) == value)
        score = matches / len(expected)
        return Evaluation(score == 1.0, score, f"Matched {matches}/{len(expected)} acceptance criteria.")
