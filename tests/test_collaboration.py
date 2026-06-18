"""Tests for autonomous agent collaboration workflows."""
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


class TestRunValidationLoop:
    """Autonomous validation loop: DQ → Schema → DQ → Catalog."""

    def test_full_loop(self, orch):
        """Complete validation loop runs all 4 steps."""
        result = orch.run_validation_loop("test_users")
        assert result["status"] == "completed"
        assert len(result["steps"]) == 4
        assert result["steps"] == ["dq_profile", "schema_drift", "dq_validate", "catalog_describe"]
        assert len(result["results"]) == 4

    def test_each_step_has_result(self, orch):
        """Each agent in the loop should return a result."""
        result = orch.run_validation_loop("test_users")
        for r in result["results"]:
            assert r["status"] == "success"
            assert "agent" in r
        assert result["results"][0]["agent"] == "dq"  # profile
        assert result["results"][2]["agent"] == "dq"  # validate

    def test_pipeline_tracked(self, orch):
        """Validation loop should persist pipeline state."""
        result = orch.run_validation_loop("test_users")
        assert result["pipeline_id"] in orch.pipelines
        stored = orch.pipelines[result["pipeline_id"]]
        assert stored["task"].startswith("validation_loop")
        assert len(stored["results"]) == 4

    def test_loop_stops_on_dq_error(self, orch):
        """If DQ profiling fails, the loop should stop early."""
        # Remove dq agent to force error
        orch.registry.unregister("dq")
        result = orch.run_validation_loop("test_users")
        assert result["status"] == "failed"
        assert result["failed_at"] == "dq_profile"
        assert len(result["results"]) == 1  # only dq attempted


class TestRunComplianceScan:
    """Compliance scan: DQ → Catalog (tag) → Schema → Observability."""

    def test_compliance_scan(self, orch):
        """Full compliance scan for PII columns."""
        result = orch.run_compliance_scan("test_users", ["email", "phone", "ssn"])
        assert result["status"] in ("completed", "completed_with_errors")
        assert result["pii_columns_checked"] == 3
        assert result["pii_tags_applied"] >= 1
        assert len(result["results"]) >= 5  # 1 dq + 3 tags + 1 schema + 1 obs

    def test_compliance_scan_no_pii(self, orch):
        """Zero PII columns should still run, just skip tagging."""
        result = orch.run_compliance_scan("test_users", [])
        assert result["status"] in ("completed", "completed_with_errors")
        assert result["pii_columns_checked"] == 0
        assert result["pii_tags_applied"] == 0

    def test_compliance_pipeline_tracked(self, orch):
        """Compliance scan should persist pipeline state."""
        result = orch.run_compliance_scan("test_users", ["email"])
        assert result["pipeline_id"] in orch.pipelines
        stored = orch.pipelines[result["pipeline_id"]]
        assert stored["task"].startswith("compliance_scan")
        assert len(stored["results"]) >= 4

    def test_compliance_chain_order(self, orch):
        """Agents should run in the correct order."""
        result = orch.run_compliance_scan("test_users", ["email"])
        chain = result["pipeline"]
        assert chain == ["dq", "catalog", "schema", "observability"]
