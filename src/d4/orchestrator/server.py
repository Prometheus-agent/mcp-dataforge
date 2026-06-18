import uuid
from typing import Optional
from d4.registry.agent_registry import AgentRegistry
from d4.models.core import AgentStep


def create_orchestrator(registry: Optional[AgentRegistry] = None):
    """Create an orchestrator state object."""
    if registry is None:
        registry = AgentRegistry()
    return {
        "_registry": registry,
        "_pipelines": {},
    }


def route_task(state: dict, task: str, context: Optional[dict] = None) -> dict:
    """Parse a task description and return a multi-agent execution plan.

    Uses simple keyword-based routing to determine which agents
    should be involved.
    """
    task_lower = task.lower()
    registry: AgentRegistry = state["_registry"]
    agents = registry.list_agents()

    relevant_agents = []

    # Data quality keywords
    dq_keywords = ["null", "quality", "profile", "anomaly", "validate", "freshness", "accuracy"]
    if any(kw in task_lower for kw in dq_keywords):
        dq_agent = registry.find_by_capability("data_quality")
        if dq_agent:
            relevant_agents.append(dq_agent[0])

    # Pipeline keywords
    pipeline_keywords = ["pipeline", "sql", "etl", "elt", "transform", "generate", "spark", "dbt"]
    if any(kw in task_lower for kw in pipeline_keywords):
        pipeline_agent = registry.find_by_capability("sql")
        if pipeline_agent:
            relevant_agents.append(pipeline_agent[0])

    # Schema keywords
    schema_keywords = ["schema", "drift", "migration", "column", "lineage", "alter"]
    if any(kw in task_lower for kw in schema_keywords):
        schema_agent = registry.find_by_capability("schema")
        if schema_agent:
            relevant_agents.append(schema_agent[0])

    # If no agents matched, use the first available one
    if not relevant_agents and registry.list_agents():
        relevant_agents = [registry.list_agents()[0]]

    # Build execution plan
    pipeline_id = f"pipeline_{uuid.uuid4().hex[:8]}"
    plan = []
    for agent in relevant_agents:
        plan.append(AgentStep(
            agent=agent.name,
            tool="execute",
            params={"task": task, "context": context or {}},
        ).model_dump())

    # Track pipeline
    state["_pipelines"][pipeline_id] = {
        "status": "planned",
        "task": task,
        "plan": plan,
        "results": [],
    }

    return {
        "pipeline_id": pipeline_id,
        "summary": f"Planned {len(plan)} agent(s) for task: {task[:60]}...",
        "plan": plan,
    }


def list_agents(state: dict) -> list[dict]:
    """List all registered agents."""
    registry: AgentRegistry = state["_registry"]
    return [a.model_dump() for a in registry.list_agents()]


def get_pipeline_status(state: dict, pipeline_id: str) -> dict:
    """Get the status of a running or completed pipeline."""
    pipeline = state["_pipelines"].get(pipeline_id)
    if pipeline is None:
        return {
            "pipeline_id": pipeline_id,
            "status": "not_found",
        }
    return {
        "pipeline_id": pipeline_id,
        "status": pipeline["status"],
        "task": pipeline["task"],
        "plan": pipeline["plan"],
    }
