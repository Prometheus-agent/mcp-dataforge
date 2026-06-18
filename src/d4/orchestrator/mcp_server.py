"""FastMCP server exposing the orchestrator as MCP tools for Claude Code."""
from mcp.server.fastmcp import FastMCP
from d4.orchestrator.server import Orchestrator
from d4.config.loader import find_config, load_config
from d4.registry.agent_registry import AgentRegistry

# Singleton state — persists across MCP tool calls
_orchestrator: Orchestrator | None = None


def _get_orchestrator() -> Orchestrator:
    """Get or create the orchestrator singleton with config-loaded agents."""
    global _orchestrator
    if _orchestrator is None:
        config_path = find_config()
        if config_path:
            config = load_config(config_path)
            registry = AgentRegistry()
            registry.load_from_config(config)
        else:
            registry = AgentRegistry()
        _orchestrator = Orchestrator(registry=registry)
    return _orchestrator


# Create FastMCP server
mcp = FastMCP(
    "DataForge",
    instructions="Multi-agent data engineering framework — route tasks to specialist agents",
)


@mcp.tool()
def route_task(task: str, context: dict | None = None) -> dict:
    """Analyze a data engineering task, plan which specialist agents should handle it, and return an execution plan. Agents include Pipeline (SQL/ETL), Data Quality (profiling/validation), Schema (drift/migration), Catalog (discovery/docs), Observability (health/cost), and Orchestration (DAG/scheduling)."""
    return _get_orchestrator().route_task(task, context)


@mcp.tool()
def list_agents() -> list[dict]:
    """List all available data engineering specialist agents and their capabilities (SQL processing, data quality, schema management, etc.)."""
    return _get_orchestrator().list_agents()


@mcp.tool()
def get_pipeline_status(pipeline_id: str) -> dict:
    """Get the current status and execution plan for a previously submitted pipeline by its pipeline_id."""
    return _get_orchestrator().get_pipeline_status(pipeline_id)


def run_stdio():
    """Run the MCP server on stdio transport (for Claude Code integration)."""
    mcp.run(transport="stdio")
