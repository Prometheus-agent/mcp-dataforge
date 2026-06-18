"""Tests for core data models."""
import pytest
from pydantic import ValidationError
from d4.models.core import (
    Task,
    AgentStep,
    AgentResponse,
    ToolInfo,
    Capability,
    AgentInfo,
)


class TestAgentStep:
    def test_minimal(self):
        step = AgentStep(agent="pipeline", tool="debug_sql")
        assert step.agent == "pipeline"
        assert step.tool == "debug_sql"
        assert step.params == {}
        assert step.depends_on == []
        assert step.parallel is False

    def test_with_params(self):
        step = AgentStep(
            agent="pipeline",
            tool="generate_pipeline",
            params={"source": "orders", "target": "orders_clean"},
            depends_on=["step_1"],
            parallel=True,
        )
        assert step.params["source"] == "orders"
        assert step.depends_on == ["step_1"]


class TestTask:
    def test_required_fields(self):
        task = Task(id="t1", description="profile orders", session_id="s1")
        assert task.context == {}
        assert task.agent_plan == []

    def test_with_plan(self):
        step = AgentStep(agent="dq", tool="profile_data")
        task = Task(
            id="t2",
            description="check quality",
            session_id="s1",
            agent_plan=[step],
        )
        assert len(task.agent_plan) == 1


class TestAgentResponse:
    def test_minimal(self):
        resp = AgentResponse(status="success", summary="done")
        assert resp.confidence == 0.0
        assert resp.artifacts == {}
        assert resp.requires_approval is False
        assert resp.error is None

    def test_error_response(self):
        resp = AgentResponse(
            status="error",
            summary="failed",
            error="Connection timeout",
        )
        assert resp.error == "Connection timeout"

    def test_pending_approval(self):
        resp = AgentResponse(
            status="pending_approval",
            summary="ALTER TABLE orders DROP COLUMN temp",
            requires_approval=True,
        )
        assert resp.requires_approval is True


class TestToolInfo:
    def test_creation(self):
        tool = ToolInfo(name="debug_sql", description="Analyze SQL query")
        assert tool.parameters == {}


class TestCapability:
    def test_creation(self):
        tool = ToolInfo(name="debug_sql", description="debug sql")
        cap = Capability(name="sql_analysis", tools=[tool])
        assert cap.name == "sql_analysis"
        assert len(cap.tools) == 1


class TestAgentInfo:
    def test_creation(self):
        agent = AgentInfo(
            name="pipeline",
            command="python -m d4.agents.pipeline.server",
            capabilities=["sql", "spark"],
        )
        assert agent.transport == "stdio"

    def test_empty_name(self):
        with pytest.raises(ValidationError):
            AgentInfo(name="", command="echo hi", capabilities=["x"])
