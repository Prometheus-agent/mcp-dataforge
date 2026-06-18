"""Catalog Agent — standalone MCP server (SSE mode)."""
from mcp.server.fastmcp import FastMCP
from d4.agents.catalog.server import search, describe, impact_analysis, tag

mcp = FastMCP("Catalog Agent")

@mcp.tool()
def search_tool(query: str, scope: str = "all") -> dict:
    """Search for tables, columns, and tags matching a query."""
    return search(query, scope)

@mcp.tool()
def describe_tool(table: str, include_columns: bool = True) -> dict:
    """Get documentation for a table."""
    return describe(table, include_columns)

@mcp.tool()
def impact_analysis_tool(table: str, changes: list[dict]) -> dict:
    """Analyze impact of schema changes on downstream dependencies."""
    return impact_analysis(table, changes)

@mcp.tool()
def tag_tool(entity_type: str, entity_name: str, tags: list[str], action: str = "add") -> dict:
    """Add or remove tags from a table or column."""
    return tag(entity_type, entity_name, tags, action)


def run(transport: str = "stdio", port: int = 9004):
    mcp.run(transport=transport, port=port)


if __name__ == "__main__":
    run()
