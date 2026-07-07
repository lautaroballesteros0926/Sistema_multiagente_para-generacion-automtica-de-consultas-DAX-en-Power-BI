from __future__ import annotations

from mcp_server.powerbi.client import client


async def get_schema() -> dict:
    schema = await client.fetch_schema()
    return schema.model_dump()


async def get_tables() -> list[dict]:
    return await client.fetch_tables()


async def get_relationships() -> list[dict]:
    return await client.fetch_relationships()


async def get_measures() -> list[dict]:
    return await client.fetch_measures()
