from __future__ import annotations

from typing import TypedDict

from models import DAXQuery, EvaluationResult


class AgentState(TypedDict):
    question: str
    dax_query: DAXQuery | None
    evaluation: EvaluationResult | None
    iteration: int
    max_iterations: int
    final_result: dict | None
