from __future__ import annotations

from mcp_server.powerbi.client import client


async def execute_dax(dax_query: str, max_rows: int = 100) -> dict:
    return await client.execute_query(dax_query, max_rows=max_rows)
