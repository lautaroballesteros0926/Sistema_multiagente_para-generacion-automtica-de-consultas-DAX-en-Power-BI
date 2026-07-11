from __future__ import annotations

import pytest

from mcp_server.powerbi.client import PowerBIClient
from mcp_server.tools.execution_tools import execute_dax
from mcp_server.tools.schema_tools import (
    get_measures,
    get_relationships,
    get_schema,
    get_tables,
)
from mcp_server.tools.validation_tools import validate_syntax
from models import SchemaContext

VALID_QUERY = 'EVALUATE SUMMARIZECOLUMNS(Productos[Categoria], "Total Ventas", [Total Ventas])'


@pytest.fixture
def client() -> PowerBIClient:
    return PowerBIClient(use_mock=True)


async def test_fetch_schema_returns_five_tables(client: PowerBIClient) -> None:
    schema = await client.fetch_schema()
    assert isinstance(schema, SchemaContext)
    assert len(schema.tables) == 5
    assert "Ventas" in schema.table_names()


async def test_fetch_tables_relationships_measures(client: PowerBIClient) -> None:
    tables = await client.fetch_tables()
    relationships = await client.fetch_relationships()
    measures = await client.fetch_measures()

    assert len(tables) == 5
    assert len(relationships) == 4
    assert {m["name"] for m in measures} == {
        "Total Ventas",
        "Cantidad Total",
        "Ventas Anio Anterior",
        "Ticket Promedio",
    }


async def test_validate_dax_accepts_valid_query(client: PowerBIClient) -> None:
    result = await client.validate_dax(VALID_QUERY)
    assert result["valid"] is True
    assert result["error"] is None


async def test_validate_dax_rejects_missing_evaluate(client: PowerBIClient) -> None:
    result = await client.validate_dax('SUMMARIZECOLUMNS(Productos[Categoria])')
    assert result["valid"] is False
    assert "EVALUATE" in result["error"]


async def test_validate_dax_rejects_unbalanced_parens(client: PowerBIClient) -> None:
    result = await client.validate_dax('EVALUATE ROW("x", [Total Ventas]')
    assert result["valid"] is False
    assert "aréntesis" in result["error"]


async def test_validate_dax_rejects_unknown_table(client: PowerBIClient) -> None:
    result = await client.validate_dax('EVALUATE ROW("x", Inexistente[Col])')
    assert result["valid"] is False
    assert "Inexistente" in result["error"]


async def test_validate_dax_accepts_single_quoted_table(client: PowerBIClient) -> None:
    result = await client.validate_dax("EVALUATE ROW(\"x\", 'Ventas'[ImporteTotal])")
    assert result["valid"] is True
    assert result["error"] is None


async def test_validate_dax_rejects_single_quoted_unknown_table(client: PowerBIClient) -> None:
    result = await client.validate_dax("EVALUATE ROW(\"x\", 'TablaFalsa'[Col])")
    assert result["valid"] is False
    assert "TablaFalsa" in result["error"]


async def test_validate_dax_rejects_double_quoted_table(client: PowerBIClient) -> None:
    result = await client.validate_dax('EVALUATE ROW("x", "Productos"[Categoria])')
    assert result["valid"] is False
    assert "comillas dobles" in result["error"]


async def test_execute_query_fabricates_rows_for_valid_query(client: PowerBIClient) -> None:
    result = await client.execute_query(VALID_QUERY, max_rows=3)
    assert result["error"] is None
    assert result["row_count"] == 3
    assert len(result["rows"]) == 3
    assert all("Productos[Categoria]" in row and "[Total Ventas]" in row for row in result["rows"])


async def test_execute_query_returns_error_for_invalid_query(client: PowerBIClient) -> None:
    result = await client.execute_query('SUMMARIZECOLUMNS(Productos[Categoria])')
    assert result["row_count"] == 0
    assert result["error"] is not None


async def test_execute_query_fabricates_rows_for_single_quoted_table(client: PowerBIClient) -> None:
    query = 'EVALUATE SUMMARIZECOLUMNS(\'Productos\'[Categoria], "Total Ventas", [Total Ventas])'
    result = await client.execute_query(query, max_rows=2)
    assert result["error"] is None
    for row in result["rows"]:
        assert "Productos[Categoria]" in row
        assert "[Total Ventas]" in row
        assert "[Categoria]" not in row  # no debe duplicarse como medida espuria


async def test_mcp_tool_wrappers_match_client_behavior() -> None:
    schema_dict = await get_schema()
    assert len(schema_dict["tables"]) == 5

    tables = await get_tables()
    relationships = await get_relationships()
    measures = await get_measures()
    assert len(tables) == 5
    assert len(relationships) == 4
    assert len(measures) == 4

    validation = await validate_syntax(VALID_QUERY)
    assert validation["valid"] is True

    execution = await execute_dax(VALID_QUERY, max_rows=2)
    assert execution["row_count"] == 2


def test_server_registers_all_six_tools() -> None:
    import asyncio

    from mcp_server.server import mcp

    async def _list_names() -> list[str]:
        tools = await mcp.list_tools()
        return [t.name for t in tools]

    names = asyncio.run(_list_names())
    assert set(names) == {
        "get_schema",
        "get_tables",
        "get_relationships",
        "get_measures",
        "validate_syntax",
        "execute_dax",
    }
