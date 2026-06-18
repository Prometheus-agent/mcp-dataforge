import pytest
from d4.orchestrator.mcp_server import _get_orchestrator, route_task, list_agents, get_pipeline_status
from d4.models.core import AgentInfo
from d4.registry.agent_registry import AgentRegistry


@pytest.fixture(autouse=True)
def reset_orchestrator():
    """Reset the singleton before each test."""
    import d4.orchestrator.mcp_server as srv
    srv._orchestrator = None


@pytest.fixture
def seeded_orchestrator():
    """Create an orchestrator with pre-registered agents."""
    registry = AgentRegistry()
    registry.register(AgentInfo(name="pipeline", command="cmd", capabilities=["sql"]))
    registry.register(AgentInfo(name="dq", command="cmd", capabilities=["data_quality"]))
    registry.register(AgentInfo(name="schema", command="cmd", capabilities=["schema"]))
    registry.register(AgentInfo(name="catalog", command="cmd", capabilities=["catalog"]))
    registry.register(AgentInfo(name="observability", command="cmd", capabilities=["observability"]))
    registry.register(AgentInfo(name="orchestration", command="cmd", capabilities=["orchestration"]))
    from d4.orchestrator.server import Orchestrator
    orch = Orchestrator(registry=registry)
    import d4.orchestrator.mcp_server as srv
    srv._orchestrator = orch
    return orch


class TestMCPRouteTask:
    def test_routes_dq_task(self, seeded_orchestrator):
        result = route_task("check null rates in orders table")
        assert "pipeline_id" in result
        assert any("dq" in step["agent"] for step in result["plan"])

    def test_routes_pipeline_task(self, seeded_orchestrator):
        result = route_task("generate a pipeline to clean customer data")
        assert any("pipeline" in step["agent"] for step in result["plan"])


class TestMCPListAgents:
    def test_returns_agents(self, seeded_orchestrator):
        agents = list_agents()
        assert len(agents) == 6
        names = [a["name"] for a in agents]
        assert "pipeline" in names
        assert "dq" in names


class TestMCPGetPipelineStatus:
    def test_unknown(self, seeded_orchestrator):
        status = get_pipeline_status("nonexistent")
        assert status["status"] == "not_found"
