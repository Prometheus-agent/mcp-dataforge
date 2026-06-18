import pytest
from d4.orchestrator.server import create_orchestrator, route_task, list_agents, get_pipeline_status
from d4.models.core import AgentInfo
from d4.registry.agent_registry import AgentRegistry


@pytest.fixture
def registry():
    r = AgentRegistry()
    r.register(AgentInfo(name="pipeline", command="cmd", capabilities=["sql"]))
    r.register(AgentInfo(name="dq", command="cmd", capabilities=["data_quality"]))
    return r


@pytest.fixture
def orch(registry):
    return create_orchestrator(registry=registry)


class TestListAgents:
    def test_returns_registered_agents(self, orch):
        agents = list_agents(orch)
        assert len(agents) == 2
        names = [a["name"] for a in agents]
        assert "pipeline" in names
        assert "dq" in names


class TestGetPipelineStatus:
    def test_unknown_pipeline(self, orch):
        status = get_pipeline_status(orch, "nonexistent")
        assert status["status"] == "not_found"
        assert status["pipeline_id"] == "nonexistent"


class TestRouteTask:
    def test_dq_task_routes_to_dq(self, orch):
        result = route_task(orch, "check null rates in orders table", context={"table": "orders"})
        assert "plan" in result
        assert "summary" in result
        assert len(result["plan"]) > 0
        # Should route to data quality agent
        assert any("dq" in step.get("agent", "") for step in result["plan"])

    def test_sql_task_routes_to_pipeline(self, orch):
        result = route_task(orch, "generate a pipeline to clean customer data")
        assert len(result["plan"]) > 0
        assert any("pipeline" in step.get("agent", "") for step in result["plan"])

    def test_returns_pipeline_id(self, orch):
        result = route_task(orch, "check quality")
        assert result["pipeline_id"].startswith("pipeline_")
