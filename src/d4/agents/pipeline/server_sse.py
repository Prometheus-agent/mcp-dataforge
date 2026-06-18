"""Pipeline Agent — standalone MCP server (SSE mode)."""
from mcp.server.fastmcp import FastMCP
from d4.agents.pipeline.server import execute, generate_pipeline, debug_sql, explain_plan

mcp = FastMCP("Pipeline Agent")

@mcp.tool()
def generate_pipeline_tool(source_table: str, target_table: str, transformations: list[str] | None = None) -> dict:
    """Generate a SQL pipeline skeleton from source to target."""
    return generate_pipeline(source_table, target_table, transformations)

@mcp.tool()
def debug_sql_tool(sql: str) -> dict:
    """Analyze and format a SQL query."""
    return debug_sql(sql)

@mcp.tool()
def explain_plan_tool(sql: str) -> dict:
    """Break down a SQL query into logical operations."""
    return explain_plan(sql)


def run(transport: str = "stdio", port: int = 9001):
    mcp.run(transport=transport, port=port)


if __name__ == "__main__":
    run()
