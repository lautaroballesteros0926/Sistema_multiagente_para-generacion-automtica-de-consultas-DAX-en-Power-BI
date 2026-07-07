from __future__ import annotations

from fastmcp import FastMCP

from mcp_server.tools.execution_tools import execute_dax
from mcp_server.tools.schema_tools import (
    get_measures,
    get_relationships,
    get_schema,
    get_tables,
)
from mcp_server.tools.validation_tools import validate_syntax

mcp = FastMCP("dax-mcp-server")

mcp.tool()(get_schema)
mcp.tool()(get_tables)
mcp.tool()(get_relationships)
mcp.tool()(get_measures)
mcp.tool()(validate_syntax)
mcp.tool()(execute_dax)


if __name__ == "__main__":
    mcp.run(transport="stdio")
