from __future__ import annotations

from mcp_server.powerbi.client import client


async def validate_syntax(dax_query: str) -> dict:
    return await client.validate_dax(dax_query)
