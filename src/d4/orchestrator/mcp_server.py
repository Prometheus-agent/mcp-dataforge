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


@mcp.tool()
def execute_task(task: str, context: dict | None = None) -> dict:
    """Route a data engineering task to specialist agents, execute their tools sequentially passing context between them, and return results."""
    return _get_orchestrator().execute_task(task, context)


@mcp.tool()
def execute_custom_pipeline(pipeline: list[dict], initial_context: dict | None = None) -> dict:
    """Run a custom multi-agent pipeline where you specify each step. Each step: {"agent":"dq|pipeline|schema|catalog|observability|orchestration", "task":"...", "context":{...}}. Results pass between steps sequentially."""
    return _get_orchestrator().execute_custom_pipeline(pipeline, initial_context)


@mcp.tool()
def execute_parallel(steps: list[dict]) -> dict:
    """Run multiple agent steps in PARALLEL. Each step: {"agent":"dq|pipeline|...", "task":"...", "context":{...}}. Use for independent tasks like profiling multiple tables simultaneously. Returns merged results from all agents."""
    return _get_orchestrator().execute_parallel(steps)


@mcp.tool()
def execute_mixed_pipeline(stages: list[dict], initial_context: dict | None = None) -> dict:
    """Run a multi-stage pipeline mixing sequential and parallel phases. Stage types: {"type":"single","agent":"...","task":"..."}, {"type":"sequential","steps":[...]}, {"type":"parallel","steps":[...]}. Context flows between stages automatically. Use for complex workflows like 'profile multiple tables in parallel, then run schema detection sequentially.'"""
    return _get_orchestrator().execute_mixed_pipeline(stages, initial_context)


def run_stdio():
    """Run the MCP server on stdio transport (for Claude Code integration)."""
    mcp.run(transport="stdio")
