"""Orchestration Agent — standalone MCP server (SSE mode)."""
from mcp.server.fastmcp import FastMCP
from d4.agents.orchestration.server import (
    create_dag, manage_retry, resolve_deps, backfill,
    list_dags, pause_dag, unpause_dag, visualize_dag, get_dag_runs,
)

mcp = FastMCP("Orchestration Agent")

mcp.add_tool(create_dag)
mcp.add_tool(manage_retry)
mcp.add_tool(resolve_deps)
mcp.add_tool(backfill)
mcp.add_tool(list_dags)
mcp.add_tool(pause_dag)
mcp.add_tool(unpause_dag)
mcp.add_tool(visualize_dag)
mcp.add_tool(get_dag_runs)

def run(transport: str = "stdio", port: int = 9006):
    mcp.run(transport=transport, port=port)

if __name__ == "__main__":
    run()
