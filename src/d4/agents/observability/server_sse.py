"""Observability Agent — standalone MCP server (SSE mode)."""
from mcp.server.fastmcp import FastMCP
from d4.agents.observability.server import get_pipeline_health, alert_summary, cost_analysis, suggest_optimizations, record_run, record_alert

mcp = FastMCP("Observability Agent")

@mcp.tool()
def get_pipeline_health_tool(pipeline: str) -> dict:
    """Get health status for a pipeline."""
    return get_pipeline_health(pipeline)

@mcp.tool()
def alert_summary_tool(severity: str = "all", hours: int = 24) -> dict:
    """Get summary of alerts."""
    return alert_summary(severity, hours)

@mcp.tool()
def cost_analysis_tool(provider: str = "all", timeframe: str = "monthly") -> dict:
    """Analyze warehouse/compute costs."""
    return cost_analysis(provider, timeframe)

@mcp.tool()
def suggest_optimizations_tool(pipeline: str) -> dict:
    """Suggest performance and cost optimizations."""
    return suggest_optimizations(pipeline)


def run(transport: str = "stdio", port: int = 9005):
    mcp.run(transport=transport, port=port)


if __name__ == "__main__":
    run()
