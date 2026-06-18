"""Data Quality Agent — standalone MCP server (SSE mode)."""
from mcp.server.fastmcp import FastMCP
import duckdb
from d4.agents.dq.server import profile_data, detect_anomalies, validate_rules

mcp = FastMCP("DQ Agent")

@mcp.tool()
def profile_data_tool(table: str, columns: list[str] | None = None, sample_size: int | None = None) -> dict:
    """Profile a table: row count, column stats, null rates, distributions."""
    conn = duckdb.connect(":memory:")
    try:
        return profile_data(conn, table, columns, sample_size)
    finally:
        conn.close()

@mcp.tool()
def detect_anomalies_tool(table: str, time_column: str, metric_column: str, threshold: float = 3.0) -> dict:
    """Detect anomalies in time-series data using z-score method."""
    conn = duckdb.connect(":memory:")
    try:
        return detect_anomalies(conn, table, time_column, metric_column, threshold=threshold)
    finally:
        conn.close()

@mcp.tool()
def validate_rules_tool(table: str, rules: list[dict]) -> dict:
    """Run quality rules against a table."""
    conn = duckdb.connect(":memory:")
    try:
        return validate_rules(conn, table, rules)
    finally:
        conn.close()


def run(transport: str = "stdio", port: int = 9002):
    mcp.run(transport=transport, port=port)


if __name__ == "__main__":
    run()
