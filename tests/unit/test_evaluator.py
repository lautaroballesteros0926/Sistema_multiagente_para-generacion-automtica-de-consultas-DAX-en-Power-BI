from __future__ import annotations

import json
from unittest.mock import AsyncMock

import pytest

from agents.evaluator_agent import EvaluatorAgent
from models import DAXQuery, Decision

SCHEMA_DICT = {
    "tables": [
        {"name": "Ventas", "table_type": "fact", "columns": [
            {"name": "ImporteTotal", "data_type": "decimal", "is_key": False},
        ]},
        {"name": "Productos", "table_type": "dimension", "columns": [
            {"name": "Categoria", "data_type": "string", "is_key": False},
        ]},
    ],
    "relationships": [],
    "measures": [
        {"name": "Total Ventas", "expression": "SUM(Ventas[ImporteTotal])", "table": "Ventas"},
    ],
}


@pytest.fixture
def agent() -> EvaluatorAgent:
    return EvaluatorAgent(model="test-model", temperature=0.0)


@pytest.fixture
def dax_query() -> DAXQuery:
    return DAXQuery(
        query_text='EVALUATE SUMMARIZECOLUMNS(Productos[Categoria], "Total Ventas", [Total Ventas])',
        natural_language="¿Cuál es el total de ventas por categoría?",
    )


def _mock_tool_calls(agent: EvaluatorAgent, syntax_result: dict) -> AsyncMock:
    async def fake_call_tool(name: str, **kwargs):
        if name == "get_schema":
            return SCHEMA_DICT
        if name == "validate_syntax":
            return syntax_result
        raise AssertionError(f"herramienta inesperada: {name}")

    mock = AsyncMock(side_effect=fake_call_tool)
    agent.call_tool = mock
    return mock


async def test_run_accepts_valid_high_score_response(agent: EvaluatorAgent, dax_query: DAXQuery) -> None:
    _mock_tool_calls(agent, {"valid": True, "error": None})
    agent._chat = AsyncMock(return_value=json.dumps({
        "score": 0.95,
        "decision": "ACCEPT",
        "explanation": "Usa la medida existente y responde la pregunta.",
        "semantic_coherence": 0.95,
        "schema_compliance": 1.0,
        "syntax_valid": True,
        "feedback_for_generator": None,
    }))

    result = await agent.run(dax_query.natural_language, dax_query)

    assert result.is_accepted() is True
    assert result.decision == Decision.ACCEPT
    assert result.score == 0.95


async def test_run_returns_regenerate_with_feedback(agent: EvaluatorAgent, dax_query: DAXQuery) -> None:
    _mock_tool_calls(agent, {"valid": True, "error": None})
    agent._chat = AsyncMock(return_value=json.dumps({
        "score": 0.6,
        "decision": "REGENERATE",
        "explanation": "Podría reusar una medida existente en vez de recalcular.",
        "semantic_coherence": 0.7,
        "schema_compliance": 0.9,
        "syntax_valid": True,
        "feedback_for_generator": "Usa la medida [Total Ventas] en vez de SUM manual.",
    }))

    result = await agent.run(dax_query.natural_language, dax_query)

    assert result.needs_regeneration() is True
    assert result.feedback_for_generator == "Usa la medida [Total Ventas] en vez de SUM manual."


async def test_run_falls_back_to_reject_on_invalid_json(agent: EvaluatorAgent, dax_query: DAXQuery) -> None:
    _mock_tool_calls(agent, {"valid": True, "error": None})
    agent._chat = AsyncMock(return_value="esto no es JSON")

    result = await agent.run(dax_query.natural_language, dax_query)

    assert result.decision == Decision.REJECT
    assert result.score == 0.0


async def test_run_calls_chat_with_deterministic_temperature_and_json_format(
    agent: EvaluatorAgent, dax_query: DAXQuery
) -> None:
    _mock_tool_calls(agent, {"valid": True, "error": None})
    agent._chat = AsyncMock(return_value=json.dumps({
        "score": 0.9,
        "decision": "ACCEPT",
        "explanation": "ok",
        "semantic_coherence": 0.9,
        "schema_compliance": 0.9,
        "syntax_valid": True,
        "feedback_for_generator": None,
    }))

    await agent.run(dax_query.natural_language, dax_query)

    agent._chat.assert_awaited_once()
    _, kwargs = agent._chat.call_args
    assert kwargs["temperature"] == 0.0
    assert kwargs["response_format"] == {"type": "json_object"}


async def test_run_queries_schema_and_validates_syntax(agent: EvaluatorAgent, dax_query: DAXQuery) -> None:
    mock = _mock_tool_calls(agent, {"valid": False, "error": "La tabla 'X' no existe"})
    agent._chat = AsyncMock(return_value=json.dumps({
        "score": 0.1,
        "decision": "REJECT",
        "explanation": "Referencia a tabla inexistente.",
        "semantic_coherence": 0.2,
        "schema_compliance": 0.0,
        "syntax_valid": False,
        "feedback_for_generator": None,
    }))

    result = await agent.run(dax_query.natural_language, dax_query)

    called_tool_names = [call.args[0] for call in mock.await_args_list]
    assert called_tool_names == ["get_schema", "validate_syntax"]
    assert result.syntax_valid is False
