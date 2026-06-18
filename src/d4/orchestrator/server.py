"""Orchestrator — routes tasks to specialist agents and tracks pipelines."""
import uuid
from typing import Optional
from d4.registry.agent_registry import AgentRegistry
from d4.models.core import AgentStep


class Orchestrator:
    """Orchestrator that routes tasks to specialist agents and tracks pipelines."""

    def __init__(self, registry: Optional[AgentRegistry] = None):
        self.registry = registry or AgentRegistry()
        self.pipelines: dict[str, dict] = {}

    def route_task(self, task: str, context: Optional[dict] = None) -> dict:
        """Parse a task description and return a multi-agent execution plan."""
        task_lower = task.lower()
        relevant_agents = []

        # Intent-based routing via keywords
        dq_keywords = ["null", "quality", "profile", "anomaly", "validate", "freshness", "accuracy"]
        if any(kw in task_lower for kw in dq_keywords):
            dq_agent = self.registry.find_by_capability("data_quality")
            if dq_agent:
                relevant_agents.append(dq_agent[0])

        pipeline_keywords = ["pipeline", "sql", "etl", "elt", "transform", "generate", "spark", "dbt"]
        if any(kw in task_lower for kw in pipeline_keywords):
            pipeline_agent = self.registry.find_by_capability("sql")
            if pipeline_agent:
                relevant_agents.append(pipeline_agent[0])

        schema_keywords = ["schema", "drift", "migration", "column", "lineage", "alter"]
        if any(kw in task_lower for kw in schema_keywords):
            schema_agent = self.registry.find_by_capability("schema")
            if schema_agent:
                relevant_agents.append(schema_agent[0])

        catalog_keywords = ["catalog", "search", "find", "documentation", "describe", "tag", "discover"]
        if any(kw in task_lower for kw in catalog_keywords):
            catalog_agent = self.registry.find_by_capability("catalog")
            if catalog_agent:
                relevant_agents.append(catalog_agent[0])

        observability_keywords = ["health", "monitor", "alert", "cost", "observe", "sla", "performance"]
        if any(kw in task_lower for kw in observability_keywords):
            obs_agent = self.registry.find_by_capability("observability")
            if obs_agent:
                relevant_agents.append(obs_agent[0])

        orchestration_keywords = ["dag", "schedule", "backfill", "orchestrate", "airflow", "retry", "run"]
        if any(kw in task_lower for kw in orchestration_keywords):
            orch_agent = self.registry.find_by_capability("orchestration")
            if orch_agent:
                relevant_agents.append(orch_agent[0])

        if not relevant_agents and self.registry.list_agents():
            relevant_agents = [self.registry.list_agents()[0]]

        pipeline_id = f"pipeline_{uuid.uuid4().hex[:8]}"
        plan = []
        for agent in relevant_agents:
            plan.append(AgentStep(
                agent=agent.name,
                tool="execute",
                params={"task": task, "context": context or {}},
            ).model_dump())

        self.pipelines[pipeline_id] = {
            "status": "planned",
            "task": task,
            "plan": plan,
            "results": [],
        }

        return {
            "pipeline_id": pipeline_id,
            "summary": f"Planned {len(plan)} agent(s) for task: {task[:80]}...",
            "plan": plan,
        }

    def list_agents(self) -> list[dict]:
        """List all registered agents."""
        return [a.model_dump() for a in self.registry.list_agents()]

    def get_pipeline_status(self, pipeline_id: str) -> dict:
        """Get the status of a running or completed pipeline."""
        pipeline = self.pipelines.get(pipeline_id)
        if pipeline is None:
            return {"pipeline_id": pipeline_id, "status": "not_found"}
        return {
            "pipeline_id": pipeline_id,
            "status": pipeline["status"],
            "task": pipeline["task"],
            "plan": pipeline["plan"],
        }


# Backward compatibility
def create_orchestrator(registry: Optional[AgentRegistry] = None) -> Orchestrator:
    """Create an Orchestrator instance. Legacy wrapper."""
    return Orchestrator(registry=registry)


def route_task(state: Orchestrator, task: str, context: Optional[dict] = None) -> dict:
    """Route a task. Legacy wrapper."""
    return state.route_task(task, context)


def list_agents(state: Orchestrator) -> list[dict]:
    """List agents. Legacy wrapper."""
    return state.list_agents()


def get_pipeline_status(state: Orchestrator, pipeline_id: str) -> dict:
    """Get pipeline status. Legacy wrapper."""
    return state.get_pipeline_status(pipeline_id)
