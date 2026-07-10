from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from models import DAXQuery, Decision, EvaluationResult
from orchestrator import graph as graph_module
from orchestrator.graph import build_graph
from orchestrator.state import AgentState

QUESTION = "¿Cuál es el total de ventas por categoría de producto?"


def _dax(query_text: str = 'EVALUATE ROW("x", 1)', iteration: int = 0) -> DAXQuery:
    return DAXQuery(query_text=query_text, natural_language=QUESTION, iteration=iteration)


def _evaluation(decision: Decision, feedback: str | None = None, score: float = 0.5) -> EvaluationResult:
    return EvaluationResult(
        score=score,
        decision=decision,
        explanation=f"explicación para {decision.value}",
        syntax_valid=True,
        feedback_for_generator=feedback,
    )


def _initial_state(max_iterations: int = 3) -> AgentState:
    return {
        "question": QUESTION,
        "dax_query": None,
        "evaluation": None,
        "iteration": 0,
        "max_iterations": max_iterations,
        "final_result": None,
    }


@pytest.fixture(autouse=True)
def _mock_agents(mocker):
    mocker.patch.object(graph_module._generator, "run", new_callable=AsyncMock)
    mocker.patch.object(graph_module._evaluator, "run", new_callable=AsyncMock)
    return graph_module._generator, graph_module._evaluator


async def test_accept_on_first_iteration(_mock_agents) -> None:
    generator, evaluator = _mock_agents
    generator.run.return_value = _dax()
    evaluator.run.return_value = _evaluation(Decision.ACCEPT, score=0.95)

    graph = build_graph()
    result = await graph.ainvoke(_initial_state())

    assert result["final_result"]["decision"] == Decision.ACCEPT
    assert result["final_result"]["iterations"] == 1
    generator.run.assert_awaited_once_with(QUESTION, feedback=None)
    evaluator.run.assert_awaited_once()


async def test_regenerate_then_accept_on_second_iteration(_mock_agents) -> None:
    generator, evaluator = _mock_agents
    generator.run.side_effect = [_dax("EVALUATE ROW(\"a\", 1)"), _dax("EVALUATE ROW(\"b\", 2)")]
    evaluator.run.side_effect = [
        _evaluation(Decision.REGENERATE, feedback="usa la medida existente", score=0.6),
        _evaluation(Decision.ACCEPT, score=0.9),
    ]

    graph = build_graph()
    result = await graph.ainvoke(_initial_state())

    assert result["final_result"]["decision"] == Decision.ACCEPT
    assert result["final_result"]["iterations"] == 2
    assert generator.run.await_count == 2
    second_call_kwargs = generator.run.await_args_list[1].kwargs
    assert second_call_kwargs["feedback"] == "usa la medida existente"


async def test_exhausts_max_iterations_then_reject(_mock_agents) -> None:
    generator, evaluator = _mock_agents
    generator.run.return_value = _dax()
    evaluator.run.return_value = _evaluation(Decision.REGENERATE, feedback="sigue sin convencer", score=0.6)

    graph = build_graph()
    result = await graph.ainvoke(_initial_state(max_iterations=2))

    assert result["final_result"]["decision"] == Decision.REJECT
    assert result["final_result"]["iterations"] == 2
    assert generator.run.await_count == 2
    assert evaluator.run.await_count == 2
