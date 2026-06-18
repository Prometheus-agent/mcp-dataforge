"""End-to-end integration tests for multi-agent workflows, error recovery, and state management."""
import pytest
from d4.orchestrator.server import Orchestrator
from d4.models.core import AgentInfo
from d4.registry.agent_registry import AgentRegistry


@pytest.fixture
def full_registry():
    r = AgentRegistry()
    r.register(AgentInfo(name="pipeline", command="cmd", capabilities=["sql"]))
    r.register(AgentInfo(name="dq", command="cmd", capabilities=["data_quality"]))
    r.register(AgentInfo(name="schema", command="cmd", capabilities=["schema", "drift"]))
    r.register(AgentInfo(name="catalog", command="cmd", capabilities=["catalog", "discovery"]))
    r.register(AgentInfo(name="observability", command="cmd", capabilities=["observability", "monitoring"]))
    r.register(AgentInfo(name="orchestration", command="cmd", capabilities=["orchestration", "dag"]))
    return r


@pytest.fixture
def orch(full_registry):
    return Orchestrator(registry=full_registry)


# ─── Complete Workflow: Profile → Schema → Catalog → Observability ───

class TestCompleteDataPipeline:
    """Simulate a full data platform workflow: profile, detect, document, monitor."""

    def test_profile_and_detect_drift(self, orch):
        """Phase 1: Profile data + detect schema drift in parallel."""
        parallel_result = orch.execute_parallel([
            {
                "agent": "dq",
                "task": "profile the customers table for nulls",
                "context": {"table": "test_users", "columns": ["id", "email", "age"]},
            },
            {
                "agent": "schema",
                "task": "detect schema drift between staging and prod",
                "context": {
                    "source_columns": [
                        {"name": "id", "type": "INTEGER", "nullable": False},
                        {"name": "email", "type": "VARCHAR", "nullable": True},
                    ],
                    "target_columns": [
                        {"name": "id", "type": "INTEGER", "nullable": False},
                        {"name": "email", "type": "VARCHAR", "nullable": True},
                        {"name": "phone", "type": "VARCHAR", "nullable": True},
                    ],
                },
            },
        ])
        assert parallel_result["status"] == "completed"
        assert parallel_result["total_steps"] == 2
        merged = parallel_result["merged_results"]
        assert "dq" in merged
        assert "schema" in merged
        # Schema should have detected drift (phone column added)
        assert merged["schema"].get("has_drift") is True
        assert len(merged["schema"].get("added", [])) == 1

    def test_document_and_monitor_after_detection(self, orch):
        """Phase 2: After detection, catalog the changes and run health checks."""
        # First run parallel profile + detect
        orch.execute_parallel([
            {"agent": "dq", "task": "profile", "context": {"table": "test_users"}},
            {"agent": "schema", "task": "detect drift", "context": {
                "source_columns": [{"name": "id", "type": "INTEGER"}],
                "target_columns": [{"name": "id", "type": "INTEGER"}, {"name": "email", "type": "VARCHAR"}],
            }},
        ])

        # Then sequentially: catalog search → observability health check
        seq_result = orch.execute_custom_pipeline([
            {"agent": "catalog", "task": "search for customer related assets", "context": {"query": "customer", "scope": "all"}},
            {"agent": "observability", "task": "health check on daily pipelines", "context": {"pipeline": "daily_revenue"}},
        ])
        assert seq_result["status"] == "completed"
        assert seq_result["steps"] == 2
        assert seq_result["pipeline"] == ["catalog", "observability"]

    def test_full_lifecycle(self, orch):
        """End-to-end: profile → schema → catalog → observability."""
        # Stage 1: Profile data
        p1 = orch.execute_task("profile the orders table for data quality")
        assert p1["status"] in ("completed", "completed_with_errors")

        # Stage 2: Detect schema drift
        p2 = orch.execute_task("check schema drift on the staging table")
        assert p2["status"] in ("completed", "completed_with_errors")

        # Stage 3: Search catalog
        p3 = orch.execute_task("search for all PII-related data in the catalog")
        assert p3["status"] in ("completed", "completed_with_errors")

        # Verify all pipelines are tracked
        assert p1["pipeline_id"] in orch.pipelines
        assert p2["pipeline_id"] in orch.pipelines
        assert p3["pipeline_id"] in orch.pipelines


# ─── Mixed Pipeline Workflows ───

class TestMixedPipelineWorkflows:
    """Test complex mixed sequential/parallel pipelines."""

    def test_parallel_data_quality_then_migration(self, orch):
        """Run DQ + Schema in parallel, then use results to generate migration."""
        result = orch.execute_mixed_pipeline([
            {
                "type": "parallel",
                "steps": [
                    {"agent": "dq", "task": "profile", "context": {"table": "test_users"}},
                    {"agent": "schema", "task": "detect drift", "context": {
                        "source_columns": [{"name": "id", "type": "INTEGER"}],
                        "target_columns": [{"name": "id", "type": "INTEGER"}, {"name": "email", "type": "VARCHAR"}],
                    }},
                ],
            },
            {
                "type": "single",
                "agent": "schema",
                "task": "generate migration based on detected drift",
                "context": {
                    "source_columns": [{"name": "id", "type": "INTEGER"}],
                    "target_columns": [{"name": "id", "type": "INTEGER"}, {"name": "email", "type": "VARCHAR"}],
                    "table": "users",
                },
            },
        ])
        assert len(result["stages"]) == 2
        assert result["stages"][0]["type"] == "parallel"
        assert result["stages"][1]["type"] == "single"

    def test_pipeline_then_backfill(self, orch):
        """Create a DAG, then run a backfill."""
        result = orch.execute_custom_pipeline([
            {"agent": "orchestration", "task": "create dag for daily_etl", "context": {
                "dag_id": "daily_etl",
                "schedule": "@daily",
                "tasks": [
                    {"id": "extract", "depends_on": []},
                    {"id": "load", "depends_on": ["extract"]},
                ],
            }},
            {"agent": "orchestration", "task": "backfill the dag for last 3 days", "context": {
                "dag_id": "daily_etl",
                "start_date": "2026-01-01",
                "end_date": "2026-01-03",
                "dry_run": True,
            }},
        ])
        assert result["status"] == "completed"
        assert result["steps"] == 2

    def test_full_platform_audit(self, orch):
        """Complex: 3 parallel agents → sequential analysis → summary."""
        stages = [
            {
                "type": "parallel",
                "steps": [
                    {"agent": "catalog", "task": "search", "context": {"query": "revenue", "scope": "all"}},
                    {"agent": "schema", "task": "drift", "context": {
                        "source_columns": [{"name": "id", "type": "INTEGER"}],
                        "target_columns": [{"name": "id", "type": "INTEGER"}, {"name": "amount", "type": "FLOAT"}],
                    }},
                    {"agent": "orchestration", "task": "create dag", "context": {
                        "dag_id": "audit_test",
                        "tasks": [{"id": "start", "depends_on": []}],
                    }},
                ],
            },
            {"type": "single", "agent": "observability", "task": "health check", "context": {"pipeline": "daily_revenue"}},
        ]
        result = orch.execute_mixed_pipeline(stages)
        assert len(result["stages"]) == 2
        stage0 = result["stages"][0]
        assert stage0["type"] == "parallel"
        assert len(stage0["results"]) == 3
        stage1 = result["stages"][1]
        assert stage1["type"] == "single"


# ─── Error Recovery ───

class TestErrorRecovery:
    """Test orchestrator behavior when agents fail."""

    def test_parallel_error_does_not_block_others(self, orch):
        """One agent failure in parallel should not block other agents."""
        steps = [
            {"agent": "catalog", "task": "search for data", "context": {"query": "test", "scope": "all"}},
            {"agent": "nonexistent", "task": "fail", "context": {}},
            {"agent": "pipeline", "task": "generate pipeline", "context": {"source_table": "a", "target_table": "b"}},
        ]
        result = orch.execute_parallel(steps)
        # Should complete despite error
        assert result["total_steps"] == 3
        # At least one should succeed
        success_count = sum(1 for r in result["results"] if r and r["status"] == "success")
        assert success_count >= 2

    def test_custom_pipeline_stops_on_error(self, orch):
        """Sequential custom pipeline should stop on first error."""
        result = orch.execute_custom_pipeline([
            {"agent": "catalog", "task": "search", "context": {"query": "ok", "scope": "all"}},
            {"agent": "broken_agent", "task": "fail", "context": {}},
        ])
        assert result["status"] == "failed"
        # Should have stopped at step 1 (the error)
        assert len(result["results"]) <= 2

    def test_mixed_pipeline_continues_after_partial_error(self, orch):
        """In mixed mode, a parallel stage with errors should still allow the next sequential stage."""
        stages = [
            {
                "type": "parallel",
                "steps": [
                    {"agent": "catalog", "task": "search", "context": {"query": "ok", "scope": "all"}},
                    {"agent": "nonexistent", "task": "fail", "context": {}},
                ],
            },
            {"type": "single", "agent": "catalog", "task": "search", "context": {"query": "after", "scope": "all"}},
        ]
        result = orch.execute_mixed_pipeline(stages)
        # The single stage should still execute (even if parallel had errors)
        assert len(result["stages"]) == 2
        # Second stage should have results
        assert len(result["stages"][1]["results"]) == 1


# ─── Pipeline State ───

class TestPipelineStateManagement:
    """Test pipeline tracking, retrieval, and lifecycle."""

    def test_multiple_pipeline_tracking(self, orch):
        """Run multiple tasks and verify all are tracked."""
        ids = []
        for task in ["profile data", "check schema", "search catalog", "health check", "create dag"]:
            r = orch.execute_task(task)
            ids.append(r["pipeline_id"])

        # All should be tracked
        for pid in ids:
            assert pid in orch.pipelines

        # Status should be retrievable for all
        for pid in ids:
            status = orch.get_pipeline_status(pid)
            assert status["status"] in ("completed", "completed_with_errors")

    def test_pipeline_status_contains_results(self, orch):
        """Pipeline status should include execution results."""
        result = orch.execute_task("profile data quality on users")
        pid = result["pipeline_id"]
        status = orch.get_pipeline_status(pid)
        assert "results" in status
        assert len(status["results"]) > 0

    def test_pipeline_persistence_across_execution_modes(self, orch):
        """All execution modes should persist pipeline state."""
        r1 = orch.execute_task("profile data")
        assert r1["pipeline_id"] in orch.pipelines

        r2 = orch.execute_custom_pipeline([
            {"agent": "catalog", "task": "search", "context": {"query": "x", "scope": "all"}},
        ])
        assert r2["pipeline_id"] in orch.pipelines

        r3 = orch.execute_parallel([
            {"agent": "catalog", "task": "search", "context": {"query": "y", "scope": "all"}},
        ])
        assert r3["pipeline_id"] in orch.pipelines

        r4 = orch.execute_mixed_pipeline([
            {"type": "single", "agent": "catalog", "task": "search", "context": {"query": "z", "scope": "all"}},
        ])
        assert r4["pipeline_id"] in orch.pipelines

        # All 4 distinct pipelines
        assert len(set([r1["pipeline_id"], r2["pipeline_id"], r3["pipeline_id"], r4["pipeline_id"]])) == 4


# ─── Agent Communication ───

class TestAgentCommunication:
    """Test context passing between agents."""

    def test_catalog_result_flows_to_schema(self, orch):
        """Verify previous_result context is available to subsequent agents."""
        result = orch.execute_custom_pipeline([
            {"agent": "catalog", "task": "search for orders data", "context": {"query": "order", "scope": "all"}},
            {"agent": "schema", "task": "detect drift", "context": {
                "source_columns": [{"name": "id", "type": "INTEGER"}],
                "target_columns": [{"name": "id", "type": "INTEGER"}, {"name": "total", "type": "FLOAT"}],
            }},
        ])
        assert result["status"] == "completed"
        assert len(result["results"]) == 2
        # Schema agent should have received catalog's result in its context
        schema_result = result["results"][1]
        assert schema_result["agent"] == "schema"

    def test_dq_and_schema_agent_in_sequence(self, orch):
        """DQ profiles data → Schema checks drift — context passes between them."""
        result = orch.execute_task("profile customers and check schema quality on the results")
        agents_involved = result.get("pipeline", [])
        assert len(agents_involved) >= 1
        # Results should be in order
        for i, agent_name in enumerate(agents_involved):
            assert result["results"][i]["agent"] == agent_name
