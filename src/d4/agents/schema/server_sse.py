"""Schema Agent — standalone MCP server (SSE mode)."""
from mcp.server.fastmcp import FastMCP
from d4.agents.schema.server import detect_drift, generate_migration, lint_schema, lineage

mcp = FastMCP("Schema Agent")

@mcp.tool()
def detect_drift_tool(source_columns: list[dict], target_columns: list[dict]) -> dict:
    """Compare two column schemas and report drift."""
    return detect_drift(source_columns, target_columns)

@mcp.tool()
def generate_migration_tool(source_columns: list[dict], target_columns: list[dict], table: str = "target_table") -> dict:
    """Generate SQL migration from source schema to target schema."""
    return generate_migration(source_columns, target_columns, table)

@mcp.tool()
def lint_schema_tool(columns: list[dict], conventions: dict | None = None) -> dict:
    """Lint a schema against naming conventions and best practices."""
    return lint_schema(columns, conventions)

@mcp.tool()
def lineage_tool(table: str, columns: list[str], transformations: list[dict]) -> dict:
    """Trace column-level lineage through transformations."""
    return lineage(table, columns, transformations)


def run(transport: str = "stdio", port: int = 9003):
    mcp.run(transport=transport, port=port)


if __name__ == "__main__":
    run()
