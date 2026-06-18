"""Tests for orchestrator — routing, sequential, parallel, and mixed pipeline execution."""
import pytest
from d4.orchestrator.server import (
    create_orchestrator, route_task, list_agents, get_pipeline_status,
)
from d4.models.core import AgentInfo
from d4.registry.agent_registry import AgentRegistry


@pytest.fixture
def registry():
    r = AgentRegistry()
    r.register(AgentInfo(name="pipeline", command="cmd", capabilities=["sql"]))
    r.register(AgentInfo(name="dq", command="cmd", capabilities=["data_quality"]))
    r.register(AgentInfo(name="schema", command="cmd", capabilities=["schema", "drift"]))
    r.register(AgentInfo(name="catalog", command="cmd", capabilities=["catalog", "discovery"]))
    r.register(AgentInfo(name="observability", command="cmd", capabilities=["observability", "monitoring"]))
    r.register(AgentInfo(name="orchestration", command="cmd", capabilities=["orchestration", "dag"]))
    return r


@pytest.fixture
def orch(registry):
    return create_orchestrator(registry=registry)


class TestListAgents:
    def test_returns_registered_agents(self, orch):
        agents = list_agents(orch)
        assert len(agents) == 6
        names = [a["name"] for a in agents]
        assert "pipeline" in names
        assert "dq" in names


class TestGetPipelineStatus:
    def test_unknown_pipeline(self, orch):
        status = get_pipeline_status(orch, "nonexistent")
        assert status["status"] == "not_found"
        assert status["pipeline_id"] == "nonexistent"

    def test_known_pipeline_after_execute(self, orch):
        result = orch.execute_task("profile data quality on orders")
        status = get_pipeline_status(orch, result["pipeline_id"])
        assert status["status"] in ("completed", "completed_with_errors")
        assert "results" in status


class TestRouteTask:
    def test_dq_task_routes_to_dq(self, orch):
        result = route_task(orch, "check null rates in orders table", context={"table": "orders"})
        assert "plan" in result
        assert "summary" in result
        assert len(result["plan"]) > 0
        assert any("dq" in step.get("agent", "") for step in result["plan"])

    def test_sql_task_routes_to_pipeline(self, orch):
        result = route_task(orch, "generate a pipeline to clean customer data")
        assert len(result["plan"]) > 0
        assert any("pipeline" in step.get("agent", "") for step in result["plan"])

    def test_returns_pipeline_id(self, orch):
        result = route_task(orch, "check quality")
        assert result["pipeline_id"].startswith("pipeline_")

    def test_multi_agent_routing(self, orch):
        result = route_task(orch, "profile customers table and detect schema drift")
        agents = {step["agent"] for step in result["plan"]}
        assert "dq" in agents
        assert "schema" in agents


class TestExecuteTask:
    def test_execute_single_agent(self, orch):
        result = orch.execute_task("generate pipeline from source to target")
        assert result["status"] in ("completed", "completed_with_errors")
        assert len(result["results"]) >= 1
        assert "pipeline_id" in result
        assert "pipeline" in result

    def test_execute_summary_includes_chain(self, orch):
        result = orch.execute_task("profile null rates in orders")
        assert "→" in result["summary"] or "agent" in result["summary"]


class TestExecuteCustomPipeline:
    def test_custom_sequential_pipeline(self, orch):
        pipeline = [
            {"agent": "catalog", "task": "search for data", "context": {"query": "customer", "scope": "all"}},
            {"agent": "schema", "task": "drift analysis", "context": {
                "source_columns": [{"name": "id", "type": "INTEGER"}],
                "target_columns": [{"name": "id", "type": "INTEGER"}, {"name": "name", "type": "VARCHAR"}],
            }},
        ]
        result = orch.execute_custom_pipeline(pipeline)
        assert result["status"] == "completed"
        assert result["steps"] == 2
        assert len(result["pipeline"]) == 2
        assert result["pipeline"][0] == "catalog"
        assert result["pipeline"][1] == "schema"

    def test_custom_pipeline_stops_on_error(self, orch):
        pipeline = [
            {"agent": "catalog", "task": "search", "context": {"query": "test", "scope": "all"}},
            {"agent": "nonexistent_agent", "task": "task", "context": {}},
        ]
        result = orch.execute_custom_pipeline(pipeline)
        assert len(result["results"]) <= 2
        assert result["status"] == "failed"

    def test_custom_pipeline_single_step(self, orch):
        pipeline = [
            {"agent": "observability", "task": "cost analysis", "context": {"provider": "all"}},
        ]
        result = orch.execute_custom_pipeline(pipeline)
        assert result["status"] == "completed"
        assert result["steps"] == 1


class TestExecuteParallel:
    def test_parallel_two_agents(self, orch):
        steps = [
            {"agent": "catalog", "task": "search for data", "context": {"query": "sales", "scope": "all"}},
            {"agent": "schema", "task": "drift analysis", "context": {
                "source_columns": [{"name": "a", "type": "INTEGER"}],
                "target_columns": [{"name": "a", "type": "INTEGER"}, {"name": "b", "type": "VARCHAR"}],
            }},
        ]
        result = orch.execute_parallel(steps)
        assert result["status"] == "completed"
        assert result["total_steps"] == 2
        assert len(result["results"]) == 2
        assert "merged_results" in result

    def test_parallel_three_agents(self, orch):
        """Run three agents concurrently to verify thread pool scaling."""
        steps = [
            {"agent": "catalog", "task": "search", "context": {"query": "x", "scope": "all"}},
            {"agent": "schema", "task": "drift analysis", "context": {
                "source_columns": [{"name": "id", "type": "INTEGER"}],
                "target_columns": [{"name": "id", "type": "INTEGER", "nullable": False}],
            }},
            {"agent": "observability", "task": "health check", "context": {"pipeline": "test"}},
        ]
        result = orch.execute_parallel(steps)
        assert result["status"] == "completed"
        assert result["total_steps"] == 3
        agents = [r["agent"] for r in result["results"] if r]
        assert "catalog" in agents
        assert "schema" in agents
        assert "observability" in agents

    def test_parallel_merged_results(self, orch):
        """Verify merged_results contains output from all agents."""
        steps = [
            {"agent": "catalog", "task": "search", "context": {"query": "test", "scope": "all"}},
            {"agent": "schema", "task": "drift analysis", "context": {
                "source_columns": [{"name": "id", "type": "INTEGER"}],
                "target_columns": [{"name": "id", "type": "BIGINT"}],
            }},
        ]
        result = orch.execute_parallel(steps)
        assert "catalog" in result["merged_results"]
        assert "schema" in result["merged_results"]

    def test_parallel_with_error(self, orch):
        """One agent error doesn't block others."""
        steps = [
            {"agent": "catalog", "task": "search", "context": {"query": "ok", "scope": "all"}},
            {"agent": "nonexistent", "task": "fail", "context": {}},
        ]
        result = orch.execute_parallel(steps)
        results_by_agent = {r["agent"]: r for r in result["results"] if r}
        assert "catalog" in results_by_agent
        assert results_by_agent["catalog"]["status"] == "success"

    def test_parallel_empty_steps(self, orch):
        result = orch.execute_parallel([])
        assert result["status"] == "completed"
        assert result["total_steps"] == 0


class TestExecuteMixedPipeline:
    def test_parallel_then_single(self, orch):
        stages = [
            {
                "type": "parallel",
                "steps": [
                    {"agent": "catalog", "task": "search", "context": {"query": "revenue", "scope": "all"}},
                    {"agent": "observability", "task": "alert summary", "context": {"severity": "all"}},
                ],
            },
            {
                "type": "single",
                "agent": "schema",
                "task": "lint schema",
                "context": {"columns": [{"name": "id", "type": "INTEGER"}]},
            },
        ]
        result = orch.execute_mixed_pipeline(stages)
        assert len(result["stages"]) == 2
        stage0 = result["stages"][0]
        assert stage0["type"] == "parallel"
        assert len(stage0["results"]) == 2
        stage1 = result["stages"][1]
        assert stage1["type"] == "single"

    def test_single_then_parallel(self, orch):
        stages = [
            {"type": "single", "agent": "catalog", "task": "describe", "context": {"query": "test", "scope": "tables"}},
            {
                "type": "parallel",
                "steps": [
                    {"agent": "schema", "task": "drift", "context": {
                        "source_columns": [{"name": "a", "type": "INTEGER"}],
                        "target_columns": [{"name": "a", "type": "INTEGER"}, {"name": "b", "type": "VARCHAR"}],
                    }},
                    {"agent": "observability", "task": "health", "context": {"pipeline": "test"}},
                ],
            },
        ]
        result = orch.execute_mixed_pipeline(stages)
        assert len(result["stages"]) == 2

    def test_mixed_three_stages(self, orch):
        stages = [
            {"type": "parallel", "steps": [
                {"agent": "catalog", "task": "search", "context": {"query": "a", "scope": "all"}},
                {"agent": "schema", "task": "drift", "context": {
                    "source_columns": [{"name": "id", "type": "INTEGER"}],
                    "target_columns": [{"name": "id", "type": "INTEGER"}],
                }},
            ]},
            {"type": "sequential", "steps": [
                {"agent": "observability", "task": "cost analysis", "context": {"provider": "all"}},
            ]},
            {"type": "single", "agent": "pipeline", "task": "generate pipeline", "context": {"source_table": "a", "target_table": "b"}},
        ]
        result = orch.execute_mixed_pipeline(stages)
        assert len(result["stages"]) == 3
        # All stage types should match even if some have errors
        assert [s["type"] for s in result["stages"]] == ["parallel", "sequential", "single"]


class TestPipelineStorage:
    def test_pipeline_persists(self, orch):
        result = orch.execute_task("profile data on users")
        assert result["pipeline_id"] in orch.pipelines

    def test_multiple_pipelines(self, orch):
        r1 = orch.execute_task("task one")
        r2 = orch.execute_task("task two")
        r3 = orch.execute_parallel([
            {"agent": "catalog", "task": "search", "context": {"query": "test", "scope": "all"}},
        ])
        assert r1["pipeline_id"] in orch.pipelines
        assert r2["pipeline_id"] in orch.pipelines
        assert r3["pipeline_id"] in orch.pipelines

    def test_pipeline_has_plan(self, orch):
        result = orch.execute_custom_pipeline([
            {"agent": "catalog", "task": "search", "context": {"query": "x", "scope": "all"}},
        ])
        stored = orch.pipelines[result["pipeline_id"]]
        assert "plan" in stored
        assert "results" in stored
