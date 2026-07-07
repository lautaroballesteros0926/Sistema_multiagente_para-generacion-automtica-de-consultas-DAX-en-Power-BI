from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from agents.generator_agent import GeneratorAgent
from models import SchemaContext

RAW_TABLES = [
    {"name": "Ventas", "table_type": "fact", "columns": [
        {"name": "ImporteTotal", "data_type": "decimal", "is_key": False},
    ]},
    {"name": "Productos", "table_type": "dimension", "columns": [
        {"name": "Categoria", "data_type": "string", "is_key": False},
    ]},
]
RAW_RELATIONSHIPS = [
    {"from_table": "Ventas", "from_column": "IdProducto", "to_table": "Productos", "to_column": "IdProducto"},
]
RAW_MEASURES = [
    {"name": "Total Ventas", "expression": "SUM(Ventas[ImporteTotal])", "table": "Ventas"},
]


@pytest.fixture
def agent() -> GeneratorAgent:
    return GeneratorAgent(model="test-model", temperature=0.2)


def _mock_tool_calls(agent: GeneratorAgent) -> None:
    async def fake_call_tool(name: str, **kwargs):
        return {
            "get_tables": RAW_TABLES,
            "get_relationships": RAW_RELATIONSHIPS,
            "get_measures": RAW_MEASURES,
        }[name]

    agent.call_tool = AsyncMock(side_effect=fake_call_tool)


async def test_gather_context_builds_schema_from_tool_calls(agent: GeneratorAgent) -> None:
    _mock_tool_calls(agent)

    schema = await agent._gather_context()

    assert isinstance(schema, SchemaContext)
    assert schema.table_names() == ["Ventas", "Productos"]
    assert schema.measure_names() == ["Total Ventas"]
    assert agent.call_tool.await_count == 3


def test_extract_dax_strips_dax_fence() -> None:
    raw = '```dax\nEVALUATE ROW("x", 1)\n```'
    assert GeneratorAgent._extract_dax(raw) == 'EVALUATE ROW("x", 1)'


def test_extract_dax_strips_plain_fence() -> None:
    raw = '```\nEVALUATE ROW("x", 1)\n```'
    assert GeneratorAgent._extract_dax(raw) == 'EVALUATE ROW("x", 1)'


def test_extract_dax_handles_response_without_fence() -> None:
    raw = '  EVALUATE ROW("x", 1)  '
    assert GeneratorAgent._extract_dax(raw) == 'EVALUATE ROW("x", 1)'


async def test_run_returns_dax_query_with_iteration_zero_when_no_feedback(agent: GeneratorAgent) -> None:
    _mock_tool_calls(agent)
    agent._chat = AsyncMock(return_value='```dax\nEVALUATE SUMMARIZECOLUMNS(Productos[Categoria], "Total Ventas", [Total Ventas])\n```')

    result = await agent.run("¿Cuál es el total de ventas por categoría?")

    assert result.query_text == 'EVALUATE SUMMARIZECOLUMNS(Productos[Categoria], "Total Ventas", [Total Ventas])'
    assert result.natural_language == "¿Cuál es el total de ventas por categoría?"
    assert result.iteration == 0
    assert result.starts_with_evaluate() is True


async def test_run_sets_iteration_one_when_feedback_provided(agent: GeneratorAgent) -> None:
    _mock_tool_calls(agent)
    agent._chat = AsyncMock(return_value="EVALUATE ROW(\"x\", 1)")

    result = await agent.run("pregunta", feedback="usa la medida existente")

    assert result.iteration == 1


async def test_run_forwards_feedback_into_prompt(agent: GeneratorAgent, mocker) -> None:
    _mock_tool_calls(agent)
    agent._chat = AsyncMock(return_value="EVALUATE ROW(\"x\", 1)")
    from prompts.generator_prompts import build_generator_prompt

    spy = mocker.patch("agents.generator_agent.build_generator_prompt", wraps=build_generator_prompt)

    await agent.run("pregunta", feedback="corrige la tabla")

    spy.assert_called_once_with("pregunta", mocker.ANY, "corrige la tabla")
