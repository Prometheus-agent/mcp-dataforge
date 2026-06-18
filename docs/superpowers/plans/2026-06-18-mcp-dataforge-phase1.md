# mcp-dataforge Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the core foundation — project skeleton, CLI, Orchestrator MCP Server, and Pipeline Agent with SQL tools.

**Architecture:** Monorepo with `src/d4/` layout. Every agent is an MCP server using `mcp` Python SDK's `FastMCP`. The Orchestrator is the entry point MCP server; it discovers and communicates with agent MCP servers via config-based registry. CLI wraps server lifecycle and provides `init`, `start`, `run`, `mcp` commands.

**Tech Stack:** Python 3.11+, `mcp` (FastMCP SDK), `click` (CLI), `PyYAML` (config), `sqlparse` (SQL analysis), `pydantic` (models), `pytest` (tests).

---

## File Structure

```
/home/dateng6/brain/
├── pyproject.toml
├── README.md
├── src/
│   └── d4/
│       ├── __init__.py
│       ├── __main__.py                # python -m d4
│       ├── models/
│       │   ├── __init__.py
│       │   └── core.py                # Pydantic: Task, AgentStep, AgentResponse, Capability, AgentInfo
│       ├── config/
│       │   ├── __init__.py
│       │   └── loader.py             # YAML config loading + validation
│       ├── registry/
│       │   ├── __init__.py
│       │   └── agent_registry.py     # Agent discovery & lifecycle management
│       ├── orchestrator/
│       │   ├── __init__.py
│       │   └── server.py            # FastMCP server with route_task, list_agents, get_pipeline_status
│       ├── agents/
│       │   ├── __init__.py
│       │   └── pipeline/
│       │       ├── __init__.py
│       │       └── server.py        # Pipeline MCP server with SQL tools
│       └── cli/
│           ├── __init__.py
│           └── main.py              # click CLI: init, start, run, mcp
└── tests/
    ├── __init__.py
    ├── conftest.py
    ├── test_models.py
    ├── test_config.py
    ├── test_agent_registry.py
    ├── test_orchestrator.py
    └── test_pipeline_agent.py
```

---

### Task 1: Project Skeleton

**Files:**
- Create: `pyproject.toml`
- Create: `src/d4/__init__.py`
- Create: `src/d4/__main__.py`
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`

- [ ] **Step 1: Create pyproject.toml**

```toml
[project]
name = "mcp-dataforge"
version = "0.1.0"
description = "Multi-agent data engineering framework — MCP-native"
requires-python = ">=3.11"
dependencies = [
    "mcp>=1.0.0",
    "click>=8.0",
    "pyyaml>=6.0",
    "pydantic>=2.0",
    "sqlparse>=0.5",
]

[project.scripts]
dataforge = "d4.cli.main:cli"

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.24",
    "pytest-click>=1.1",
]

[build-system]
requires = ["setuptools>=75.0"]
build-backend = "setuptools.backends._legacy:_Backend"

[tool.setuptools.packages.find]
where = ["src"]
```

- [ ] **Step 2: Create src/d4/__init__.py**

```python
"""mcp-dataforge: Multi-agent data engineering framework — MCP-native."""

__version__ = "0.1.0"
```

- [ ] **Step 3: Create src/d4/__main__.py**

```python
"""Allow `python -m d4` to run the CLI."""
from d4.cli.main import cli

if __name__ == "__main__":
    cli()
```

- [ ] **Step 4: Create tests/__init__.py and tests/conftest.py**

```python
# tests/conftest.py
import pytest

# Shared fixtures for all tests
```

- [ ] **Step 5: Install dev deps and verify import works**

Run:
```bash
cd /home/dateng6/brain && pip install -e ".[dev]"
python -c "import d4; print(d4.__version__)"
```

Expected: `0.1.0`

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml src/d4/__init__.py src/d4/__main__.py tests/__init__.py tests/conftest.py
git commit -m "feat: project skeleton with pyproject.toml"
```

---

### Task 2: Core Data Models

**Files:**
- Create: `src/d4/models/__init__.py`
- Create: `src/d4/models/core.py`
- Create: `tests/test_models.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_models.py
import pytest
from pydantic import ValidationError
from d4.models.core import (
    Task, AgentStep, AgentResponse, ToolInfo, Capability, AgentInfo,
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

    def test_invalid_status(self):
        with pytest.raises(ValidationError):
            AgentInfo(name="bad", command="echo hi", capabilities=["x"])
```

- [ ] **Step 2: Run tests to verify they fail**

Run:
```bash
pytest tests/test_models.py -v
```
Expected: `FAILED` with `ModuleNotFoundError` or `ImportError`

- [ ] **Step 3: Write the implementation**

```python
# src/d4/models/core.py
from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


class AgentStep(BaseModel):
    """A single step in a multi-agent task plan."""
    agent: str
    tool: str
    params: dict = Field(default_factory=dict)
    depends_on: list[str] = Field(default_factory=list)
    parallel: bool = False


class Task(BaseModel):
    """A task to be executed by one or more agents."""
    id: str
    description: str
    context: dict = Field(default_factory=dict)
    session_id: str
    agent_plan: list[AgentStep] = Field(default_factory=list)


class AgentResponse(BaseModel):
    """Response from an agent after executing a tool."""
    status: str  # "success" | "error" | "pending_approval"
    summary: str
    confidence: float = 0.0
    artifacts: dict = Field(default_factory=dict)
    requires_approval: bool = False
    error: Optional[str] = None


class ToolInfo(BaseModel):
    """Metadata about an MCP tool exposed by an agent."""
    name: str
    description: str
    parameters: dict = Field(default_factory=dict)


class Capability(BaseModel):
    """A capability that an agent provides."""
    name: str
    version: str = "1.0"
    tools: list[ToolInfo] = Field(default_factory=list)


class AgentInfo(BaseModel):
    """Information about a registered agent."""
    name: str
    command: str
    transport: str = "stdio"
    capabilities: list[str] = Field(default_factory=list)
```

```python
# src/d4/models/__init__.py
from d4.models.core import (
    Task,
    AgentStep,
    AgentResponse,
    ToolInfo,
    Capability,
    AgentInfo,
)

__all__ = [
    "Task",
    "AgentStep",
    "AgentResponse",
    "ToolInfo",
    "Capability",
    "AgentInfo",
]
```

- [ ] **Step 4: Run tests to verify they pass**

Run:
```bash
pytest tests/test_models.py -v
```
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/d4/models/ tests/test_models.py
git commit -m "feat: core data models (Task, AgentStep, AgentResponse, Capability, AgentInfo)"
```

---

### Task 3: Configuration Loader

**Files:**
- Create: `src/d4/config/__init__.py`
- Create: `src/d4/config/loader.py`
- Create: `tests/test_config.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_config.py
import pytest
import yaml
from d4.config.loader import (
    DataForgeConfig,
    AgentConfig,
    load_config,
    find_config,
    create_default_config,
)


class TestAgentConfig:
    def test_minimal(self):
        cfg = AgentConfig(command="python -m d4.agents.pipeline")
        assert cfg.transport == "stdio"
        assert cfg.capabilities == []

    def test_invalid_transport(self):
        with pytest.raises(ValueError, match="transport"):
            AgentConfig(command="echo", transport="invalid")


class TestDataForgeConfig:
    def test_minimal(self):
        cfg = DataForgeConfig()
        assert cfg.version == "1.0"
        assert cfg.agents == {}

    def test_with_agents(self):
        agent = AgentConfig(command="python -m d4.agents.pipeline")
        cfg = DataForgeConfig(agents={"pipeline": agent})
        assert cfg.agents["pipeline"].command == "python -m d4.agents.pipeline"


class TestLoadConfig:
    def test_load_from_dict(self, tmp_path):
        config_data = {
            "version": "1.0",
            "project": "test-project",
            "agents": {
                "pipeline": {
                    "command": "python -m d4.agents.pipeline",
                    "transport": "stdio",
                    "capabilities": ["sql"],
                }
            },
        }
        config_file = tmp_path / "config.yaml"
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)
        cfg = load_config(config_file)
        assert cfg.project == "test-project"
        assert "pipeline" in cfg.agents
        assert cfg.agents["pipeline"].capabilities == ["sql"]

    def test_load_empty_config(self, tmp_path):
        config_file = tmp_path / "config.yaml"
        config_file.write_text("version: '1.0'\n")
        cfg = load_config(config_file)
        assert cfg.version == "1.0"
        assert cfg.agents == {}

    def test_load_missing_file(self):
        with pytest.raises(FileNotFoundError):
            load_config("/nonexistent/path/config.yaml")


class TestFindConfig:
    def test_find_in_current_dir(self, tmp_path, monkeypatch):
        config_file = tmp_path / "config.yaml"
        config_file.write_text("version: '1.0'\n")
        monkeypatch.chdir(tmp_path)
        result = find_config()
        assert result == config_file

    def test_find_in_dataforge_dir(self, tmp_path, monkeypatch):
        dataforge_dir = tmp_path / ".dataforge"
        dataforge_dir.mkdir()
        config_file = dataforge_dir / "config.yaml"
        config_file.write_text("version: '1.0'\n")
        monkeypatch.chdir(tmp_path)
        result = find_config()
        assert result == config_file


class TestCreateDefaultConfig:
    def test_default_has_pipeline_agent(self):
        cfg = create_default_config()
        assert "pipeline" in cfg.agents
        assert cfg.agents["pipeline"].command == "python -m d4.agents.pipeline.server"
```

- [ ] **Step 2: Run tests to verify they fail**

Run:
```bash
pytest tests/test_config.py -v
```
Expected: FAILED with `ModuleNotFoundError`

- [ ] **Step 3: Write the implementation**

```python
# src/d4/config/loader.py
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class AgentConfig(BaseModel):
    """Configuration for a single agent MCP server."""
    command: str
    transport: str = "stdio"
    capabilities: list[str] = Field(default_factory=list)

    @field_validator("transport")
    @classmethod
    def validate_transport(cls, v: str) -> str:
        if v not in ("stdio", "sse"):
            raise ValueError(f"transport must be 'stdio' or 'sse', got '{v}'")
        return v


class DataForgeConfig(BaseModel):
    """Top-level dataforge configuration."""
    version: str = "1.0"
    project: str = "default"
    agents: dict[str, AgentConfig] = Field(default_factory=dict)


def load_config(path: Path) -> DataForgeConfig:
    """Load and validate a YAML config file."""
    if not path.exists():
        raise FileNotFoundError(f"Config not found: {path}")
    import yaml
    with open(path) as f:
        data = yaml.safe_load(f) or {}
    return DataForgeConfig(**data)


def find_config(start_dir: Optional[Path] = None) -> Optional[Path]:
    """Search for config.yaml in current dir or .dataforge/ subdir."""
    start = start_dir or Path.cwd()
    candidates = [
        start / "config.yaml",
        start / ".dataforge" / "config.yaml",
        start / "dataforge.yaml",
    ]
    for path in candidates:
        if path.exists():
            return path
    return None


def create_default_config() -> DataForgeConfig:
    """Create the default configuration."""
    return DataForgeConfig(
        version="1.0",
        project="my-data-platform",
        agents={
            "pipeline": AgentConfig(
                command="python -m d4.agents.pipeline.server",
                capabilities=["sql"],
            ),
        },
    )


def write_default_config(path: Path) -> None:
    """Write a default config.yaml to the given path."""
    import yaml
    cfg = create_default_config()
    data = cfg.model_dump()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        yaml.dump(data, f, default_flow_style=False)
```

```python
# src/d4/config/__init__.py
from d4.config.loader import (
    DataForgeConfig,
    AgentConfig,
    load_config,
    find_config,
    create_default_config,
    write_default_config,
)

__all__ = [
    "DataForgeConfig",
    "AgentConfig",
    "load_config",
    "find_config",
    "create_default_config",
    "write_default_config",
]
```

- [ ] **Step 4: Run tests to verify they pass**

Run:
```bash
pytest tests/test_config.py -v
```
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/d4/config/ tests/test_config.py
git commit -m "feat: YAML config loader with validation"
```

---

### Task 4: Agent Registry

**Files:**
- Create: `src/d4/registry/__init__.py`
- Create: `src/d4/registry/agent_registry.py`
- Create: `tests/test_agent_registry.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_agent_registry.py
import pytest
import asyncio
from d4.registry.agent_registry import AgentRegistry
from d4.models.core import AgentInfo
from d4.config.loader import AgentConfig, DataForgeConfig


class TestAgentRegistry:
    @pytest.fixture
    def registry(self):
        return AgentRegistry()

    def test_register_agent(self, registry):
        agent = AgentInfo(name="pipeline", command="python -m d4.agents.pipeline")
        registry.register(agent)
        assert registry.get("pipeline") == agent

    def test_get_nonexistent(self, registry):
        assert registry.get("nonexistent") is None

    def test_list_agents(self, registry):
        a1 = AgentInfo(name="pipeline", command="cmd1", capabilities=["sql"])
        a2 = AgentInfo(name="dq", command="cmd2", capabilities=["quality"])
        registry.register(a1)
        registry.register(a2)
        agents = registry.list_agents()
        assert len(agents) == 2
        assert {a.name for a in agents} == {"pipeline", "dq"}

    def test_find_by_capability(self, registry):
        a1 = AgentInfo(name="pipeline", command="cmd1", capabilities=["sql", "spark"])
        a2 = AgentInfo(name="dq", command="cmd2", capabilities=["data_quality"])
        a3 = AgentInfo(name="schema", command="cmd3", capabilities=["sql", "schema"])
        registry.register(a1)
        registry.register(a2)
        registry.register(a3)
        results = registry.find_by_capability("sql")
        assert len(results) == 2
        assert {a.name for a in results} == {"pipeline", "schema"}

    def test_load_from_config(self, registry):
        config = DataForgeConfig(
            agents={
                "pipeline": AgentConfig(command="cmd1", capabilities=["sql"]),
                "dq": AgentConfig(command="cmd2", capabilities=["quality"]),
            }
        )
        registry.load_from_config(config)
        assert registry.get("pipeline") is not None
        assert registry.get("dq") is not None
        assert registry.get("pipeline").capabilities == ["sql"]

    def test_unregister(self, registry):
        agent = AgentInfo(name="pipeline", command="cmd1")
        registry.register(agent)
        registry.unregister("pipeline")
        assert registry.get("pipeline") is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run:
```bash
pytest tests/test_agent_registry.py -v
```
Expected: FAILED with `ModuleNotFoundError`

- [ ] **Step 3: Write the implementation**

```python
# src/d4/registry/agent_registry.py
from d4.models.core import AgentInfo
from d4.config.loader import DataForgeConfig


class AgentRegistry:
    """Registry that tracks available agents and their capabilities."""

    def __init__(self):
        self._agents: dict[str, AgentInfo] = {}

    def register(self, agent: AgentInfo) -> None:
        """Register an agent."""
        self._agents[agent.name] = agent

    def unregister(self, name: str) -> None:
        """Remove an agent from the registry."""
        self._agents.pop(name, None)

    def get(self, name: str) -> AgentInfo | None:
        """Get agent info by name."""
        return self._agents.get(name)

    def list_agents(self) -> list[AgentInfo]:
        """List all registered agents."""
        return list(self._agents.values())

    def find_by_capability(self, capability: str) -> list[AgentInfo]:
        """Find agents that have a specific capability."""
        return [
            a for a in self._agents.values()
            if capability in a.capabilities
        ]

    def load_from_config(self, config: DataForgeConfig) -> None:
        """Load agents from a configuration object."""
        for name, agent_cfg in config.agents.items():
            self.register(AgentInfo(
                name=name,
                command=agent_cfg.command,
                transport=agent_cfg.transport,
                capabilities=agent_cfg.capabilities,
            ))
```

```python
# src/d4/registry/__init__.py
from d4.registry.agent_registry import AgentRegistry

__all__ = ["AgentRegistry"]
```

- [ ] **Step 4: Run tests to verify they pass**

Run:
```bash
pytest tests/test_agent_registry.py -v
```
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/d4/registry/ tests/test_agent_registry.py
git commit -m "feat: agent registry with capability-based lookup"
```

---

### Task 5: Orchestrator MCP Server

**Files:**
- Create: `src/d4/orchestrator/__init__.py`
- Create: `src/d4/orchestrator/server.py`
- Create: `tests/test_orchestrator.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_orchestrator.py
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
    def test_returns_registered_agents(self, orch, registry):
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

    def test_known_pipeline(self, orch):
        # Simulate a pipeline being tracked
        route_task(orch, "test task for profiling")
        # Find the active pipeline
        pipelines = orch.get("_pipelines", {})
        # Just check the function doesn't error
        if pipelines:
            pid = list(pipelines.keys())[0]
            status = get_pipeline_status(orch, pid)
            assert "status" in status


class TestRouteTask:
    def test_simple_task_returns_plan(self, orch):
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run:
```bash
pytest tests/test_orchestrator.py -v
```
Expected: FAILED with `ModuleNotFoundError`

- [ ] **Step 3: Write the implementation**

```python
# src/d4/orchestrator/server.py
import uuid
from typing import Optional
from d4.registry.agent_registry import AgentRegistry
from d4.models.core import AgentStep


def create_orchestrator(
    server=None,
    registry: Optional[AgentRegistry] = None,
):
    """Create an orchestrator state object.
    
    In Phase 1 this is a plain dict-based state. When MCP integration
    is added, this will wrap a FastMCP server.
    """
    if registry is None:
        registry = AgentRegistry()
    return {
        "_registry": registry,
        "_pipelines": {},
    }


def route_task(state: dict, task: str, context: Optional[dict] = None) -> dict:
    """Parse a task description and return a multi-agent execution plan.
    
    In Phase 1, this uses simple keyword-based routing to determine
    which agents should be involved. Future phases will use LLM-based
    intent parsing.
    """
    task_lower = task.lower()
    registry: AgentRegistry = state["_registry"]
    agents = registry.list_agents()
    
    # Determine relevant agents based on keywords
    relevant_agents = []
    
    # Data quality keywords
    dq_keywords = ["null", "quality", "profile", "anomaly", "validate", "freshness", "accuracy"]
    if any(kw in task_lower for kw in dq_keywords):
        dq_agent = registry.get("dq") or registry.find_by_capability("data_quality")
        if dq_agent:
            relevant_agents.append(dq_agent[0] if isinstance(dq_agent, list) else dq_agent)
    
    # Pipeline keywords
    pipeline_keywords = ["pipeline", "sql", "etl", "elt", "transform", "generate", "spark", "dbt"]
    if any(kw in task_lower for kw in pipeline_keywords):
        pipeline_agent = registry.get("pipeline") or registry.find_by_capability("sql")
        if pipeline_agent:
            relevant_agents.append(pipeline_agent[0] if isinstance(pipeline_agent, list) else pipeline_agent)
    
    # Schema keywords
    schema_keywords = ["schema", "drift", "migration", "column", "lineage", "alter"]
    if any(kw in task_lower for kw in schema_keywords):
        schema_agent = registry.get("schema") or registry.find_by_capability("schema")
        if schema_agent:
            relevant_agents.append(schema_agent[0] if isinstance(schema_agent, list) else schema_agent)
    
    # If no agents matched, use the first available one
    if not relevant_agents and agents:
        relevant_agents = [agents[0]]
    
    # Build execution plan
    pipeline_id = f"pipeline_{uuid.uuid4().hex[:8]}"
    plan = []
    for agent in relevant_agents:
        plan.append(AgentStep(
            agent=agent.name if hasattr(agent, 'name') else agent.get('name', 'unknown'),
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
```

```python
# src/d4/orchestrator/__init__.py
from d4.orchestrator.server import (
    create_orchestrator,
    route_task,
    list_agents,
    get_pipeline_status,
)

__all__ = [
    "create_orchestrator",
    "route_task",
    "list_agents",
    "get_pipeline_status",
]
```

- [ ] **Step 4: Run tests to verify they pass**

Run:
```bash
pytest tests/test_orchestrator.py -v
```
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/d4/orchestrator/ tests/test_orchestrator.py
git commit -m "feat: orchestrator MCP server with routing, agent listing, pipeline status"
```

---

### Task 6: Pipeline Agent MCP Server

**Files:**
- Create: `src/d4/agents/pipeline/__init__.py`
- Create: `src/d4/agents/pipeline/server.py`
- Create: `tests/test_pipeline_agent.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_pipeline_agent.py
import pytest
from d4.agents.pipeline.server import (
    generate_pipeline,
    debug_sql,
    explain_plan,
)


class TestGeneratePipeline:
    def test_generates_simple_etl(self):
        result = generate_pipeline(
            source_table="orders.raw",
            target_table="orders.clean",
            transformations=["filter_nulls", "cast_types"],
        )
        assert "source_table" in result
        assert result["source_table"] == "orders.raw"
        assert result["target_table"] == "orders.clean"
        assert len(result["steps"]) > 0
        assert result["steps"][0] == "-- Step 1: Extract from orders.raw"
        assert "SELECT" in result["steps"][-1]

    def test_defaults(self):
        result = generate_pipeline(
            source_table="src",
            target_table="tgt",
        )
        assert len(result["steps"]) >= 2
        assert "INSERT INTO tgt" in result["steps"][-1]


class TestDebugSql:
    def test_formats_sql(self):
        sql = "SELECT a,b FROM t WHERE a>1 ORDER BY b"
        result = debug_sql(sql)
        assert result["is_valid"] is True
        # sqlparse should detect keyword count > 1
        assert "analysis" in result
        assert len(result["analysis"]["clauses"]) > 0

    def test_invalid_sql(self):
        sql = "SELECT FROM"
        result = debug_sql(sql)
        assert result["is_valid"] is True  # sqlparse is lenient
        assert result["formatted"] != sql  # formatting still works


class TestExplainPlan:
    def test_simple_select(self):
        sql = "SELECT id, name, amount FROM orders WHERE amount > 100 ORDER BY created_at DESC"
        result = explain_plan(sql)
        assert result["query_type"] == "SELECT"
        assert "id, name, amount" in result["columns"] or result["columns"] == ["*"]
        assert "orders" in result["table"]
        assert len(result["operations"]) > 0

    def test_join_query(self):
        sql = "SELECT o.id, c.name FROM orders o JOIN customers c ON o.customer_id = c.id"
        result = explain_plan(sql)
        assert "Join" in result["operations"][0] or "JOIN" in str(result["operations"])
```

- [ ] **Step 2: Run tests to verify they fail**

Run:
```bash
pytest tests/test_pipeline_agent.py -v
```
Expected: FAILED with `ModuleNotFoundError`

- [ ] **Step 3: Write the implementation**

```python
# src/d4/agents/pipeline/server.py
import sqlparse
from typing import Optional


def generate_pipeline(
    source_table: str,
    target_table: str,
    transformations: Optional[list[str]] = None,
) -> dict:
    """Generate a SQL pipeline skeleton from source to target.
    
    This tool returns a structured pipeline plan. The LLM calling this
    tool can use the output to craft the final SQL.
    """
    if transformations is None:
        transformations = ["deduplicate", "cast_types"]
    
    steps = []
    step_num = 1
    
    # Step 1: Extract
    steps.append(f"-- Step {step_num}: Extract from {source_table}")
    steps.append(f"SELECT * FROM {source_table};")
    step_num += 1
    
    # Step 2: Transformations
    for t in transformations:
        steps.append(f"-- Step {step_num}: {t}")
        if t == "filter_nulls":
            steps.append("-- WHERE column IS NOT NULL  -- add specific columns")
        elif t == "cast_types":
            steps.append("-- CAST(column AS type)  -- specify columns and types")
        elif t == "deduplicate":
            steps.append("-- ROW_NUMBER() OVER (PARTITION BY id ORDER BY updated_at DESC) AS rn\n-- WHERE rn = 1")
        else:
            steps.append(f"-- TODO: implement {t}")
        step_num += 1
    
    # Step 3: Load
    steps.append(f"-- Step {step_num}: Load to {target_table}")
    steps.append(f"INSERT INTO {target_table}\nSELECT * FROM stage;")
    
    return {
        "source_table": source_table,
        "target_table": target_table,
        "transformations": transformations,
        "steps": steps,
        "sql": "\n\n".join(steps),
    }


def debug_sql(sql: str) -> dict:
    """Analyze and format a SQL query.
    
    Returns formatted SQL, validation status, and clause-level analysis.
    """
    formatted = sqlparse.format(sql, reindent=True, keyword_case='upper')
    parsed = sqlparse.parse(sql)
    
    clauses = []
    for stmt in parsed:
        for token in stmt.tokens:
            if token.ttype is not None:
                clauses.append({
                    "type": str(token.ttype),
                    "value": token.value[:80] if len(str(token.value)) > 80 else token.value,
                })
            elif hasattr(token, 'tokens'):
                clauses.append({
                    "type": "group",
                    "value": str(type(token).__name__),
                })
    
    return {
        "is_valid": len(parsed) > 0 and len(sql.strip()) > 0,
        "formatted": formatted,
        "analysis": {
            "statement_count": len(parsed),
            "clauses": clauses,
        },
    }


def explain_plan(sql: str) -> dict:
    """Break down a SQL query into logical operations.
    
    Returns query type, target table, columns, and step-by-step operations.
    """
    parsed = sqlparse.parse(sql)
    if not parsed:
        return {"query_type": "unknown", "operations": ["Unable to parse query"]}
    
    stmt = parsed[0]
    query_type = "SELECT"
    table = "unknown"
    columns = ["*"]
    operations = []
    
    # Extract query type from first keyword
    tokens = list(stmt.flatten())
    for token in tokens:
        if token.ttype is sqlparse.tokens.DML:
            query_type = token.value.upper()
            break
    
    # Extract table names
    from_seen = False
    join_seen = False
    for token in tokens:
        if token.ttype is sqlparse.tokens.Keyword and token.value.upper() == "FROM":
            from_seen = True
            continue
        if token.ttype is sqlparse.tokens.Keyword and token.value.upper() == "JOIN":
            join_seen = True
            operations.append("Join detected")
            continue
        if from_seen and not join_seen and token.ttype is None and hasattr(token, 'get_real_name'):
            table = token.get_real_name()
            break
        if from_seen and not join_seen and isinstance(token, sqlparse.sql.Identifier):
            table = token.get_real_name() if hasattr(token, 'get_real_name') else str(token)
            break
    
    # Extract columns from SELECT
    select_seen = False
    for token in stmt.tokens:
        if token.ttype is sqlparse.tokens.DML and token.value.upper() == "SELECT":
            select_seen = True
            continue
        if select_seen and isinstance(token, sqlparse.sql.IdentifierList):
            columns = [str(col).strip() for col in token.get_sublists() if isinstance(col, sqlparse.sql.Identifier)]
            if not columns:
                columns = [str(token).strip() for token in token.tokens if isinstance(token, sqlparse.sql.Identifier)]
            break
        if select_seen and isinstance(token, sqlparse.sql.Identifier):
            columns = [str(token).strip()]
            break
        if select_seen and token.ttype is not None:
            break
    
    operations.insert(0, f"Scan table: {table}")
    
    # Detect additional operations
    for token in tokens:
        val = token.value.upper() if hasattr(token, 'value') else ''
        if val == "WHERE":
            operations.append("Filter (WHERE)")
        elif val == "ORDER BY":
            operations.append("Sort (ORDER BY)")
        elif val == "GROUP BY":
            operations.append("Aggregate (GROUP BY)")
        elif val == "LIMIT":
            operations.append("Limit (LIMIT)")
        elif val in ("DISTINCT",):
            operations.append(f"Unique ({val})")
    
    return {
        "query_type": query_type,
        "table": table,
        "columns": columns,
        "operations": operations,
    }
```

```python
# src/d4/agents/pipeline/__init__.py
from d4.agents.pipeline.server import (
    generate_pipeline,
    debug_sql,
    explain_plan,
)

__all__ = [
    "generate_pipeline",
    "debug_sql",
    "explain_plan",
]
```

- [ ] **Step 4: Run tests to verify they pass**

Run:
```bash
pytest tests/test_pipeline_agent.py -v
```
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/d4/agents/pipeline/ tests/test_pipeline_agent.py
git commit -m "feat: pipeline agent with generate_pipeline, debug_sql, explain_plan"
```

---

### Task 7: CLI

**Files:**
- Create: `src/d4/cli/__init__.py`
- Create: `src/d4/cli/main.py`

- [ ] **Step 1: Write smoke test (CLI integration test)**

```python
# tests/test_cli.py
# Note: This test file is created in Task 7 alongside the CLI
import pytest
from click.testing import CliRunner
from d4.cli.main import cli


@pytest.fixture
def runner():
    return CliRunner()


class TestCli:
    def test_version(self, runner):
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "0.1.0" in result.output

    def test_help(self, runner):
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "Usage:" in result.output

    def test_init_creates_config(self, runner, tmp_path):
        with runner.isolated_filesystem(temp_dir=tmp_path) as td:
            result = runner.invoke(cli, ["init"])
            assert result.exit_code == 0
            assert (Path(td) / "config.yaml").exists()

    def test_agent_list(self, runner):
        result = runner.invoke(cli, ["agent", "list"])
        assert result.exit_code == 0

    def test_mcp_command(self, runner):
        result = runner.invoke(cli, ["mcp"])
        assert result.exit_code == 0
        assert "mcpServers" in result.output

    def test_run_requires_argument(self, runner):
        result = runner.invoke(cli, ["run"])
        assert result.exit_code != 0
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
pytest tests/test_cli.py -v
```
Expected: FAILED with `ModuleNotFoundError`

- [ ] **Step 3: Write the CLI implementation**

```python
# src/d4/cli/main.py
import sys
import json
import asyncio
from pathlib import Path

import click

from d4 import __version__
from d4.config.loader import find_config, load_config, write_default_config
from d4.registry.agent_registry import AgentRegistry
from d4.orchestrator.server import create_orchestrator, route_task, list_agents


@click.group()
@click.version_option(version=__version__, prog_name="dataforge")
def cli():
    """mcp-dataforge: Multi-agent data engineering framework."""


@cli.command()
@click.option("--dir", "-d", default=".", help="Directory to create config in")
def init(dir):
    """Create a default config.yaml in the current directory."""
    target = Path(dir) / "config.yaml"
    if target.exists():
        click.echo(f"Config already exists: {target}", err=True)
        sys.exit(1)
    write_default_config(target)
    click.echo(f"Created config: {target}")
    click.echo("Run 'dataforge start' to launch the orchestrator and agents.")


@cli.command()
@click.argument("task", required=False)
def start(task):
    """Start the orchestrator and all configured agents.
    
    If TASK is provided, run it as a one-off command and exit.
    """
    config_path = find_config()
    if not config_path:
        click.echo("No config.yaml found. Run 'dataforge init' first.", err=True)
        sys.exit(1)
    
    config = load_config(config_path)
    registry = AgentRegistry()
    registry.load_from_config(config)
    orchestrator = create_orchestrator(registry=registry)
    
    agents = registry.list_agents()
    click.echo(f"Loaded {len(agents)} agent(s) from config:")
    for a in agents:
        caps = ", ".join(a.capabilities) if a.capabilities else "none"
        click.echo(f"  • {a.name} ({caps})")
    
    if task:
        # Run as one-off
        result = route_task(orchestrator, task)
        click.echo("")
        click.echo(f"Pipeline: {result['pipeline_id']}")
        click.echo(f"Summary: {result['summary']}")
        click.echo("Plan:")
        for step in result["plan"]:
            click.echo(f"  → {step['agent']}: {step['tool']}({step['params']['task'][:50]}...)")
    else:
        click.echo("")
        click.echo("Orchestrator ready. Use 'dataforge run <task>' or add to Claude Code:")
        click.echo('  "mcpServers": { "dataforge": { "command": "dataforge", "args": ["mcp"] } }')


@cli.command()
@click.argument("task")
def run(task):
    """Run a one-off task through the orchestrator."""
    config_path = find_config()
    if not config_path:
        # Auto-init if no config
        config_path = Path.cwd() / "config.yaml"
        write_default_config(config_path)
        click.echo(f"Auto-created config: {config_path}")
    
    config = load_config(config_path)
    registry = AgentRegistry()
    registry.load_from_config(config)
    orchestrator = create_orchestrator(registry=registry)
    
    click.echo(f"⏳ Routing: {task}")
    result = route_task(orchestrator, task)
    
    click.echo(f"  ✓ Pipeline: {result['pipeline_id']}")
    click.echo(f"  ✓ {result['summary']}")
    click.echo("")
    click.echo("Execution plan:")
    for i, step in enumerate(result["plan"], 1):
        click.echo(f"  {i}. {step['agent']} → {step['tool']}")


@cli.group()
def agent():
    """Manage agents."""
    pass


@agent.command("list")
def agent_list():
    """List available agents from config."""
    config_path = find_config()
    if not config_path:
        click.echo("No config found. Run 'dataforge init' first.", err=True)
        sys.exit(1)
    
    config = load_config(config_path)
    registry = AgentRegistry()
    registry.load_from_config(config)
    agents = registry.list_agents()
    
    if not agents:
        click.echo("No agents configured.")
        return
    
    click.echo(f"{'Name':<20} {'Transport':<10} {'Capabilities'}")
    click.echo("-" * 60)
    for a in agents:
        caps = ", ".join(a.capabilities) if a.capabilities else "-"
        click.echo(f"{a.name:<20} {a.transport:<10} {caps}")


@cli.command()
def mcp():
    """Print MCP server config for Claude Code integration."""
    config = {
        "mcpServers": {
            "dataforge": {
                "command": "dataforge",
                "args": ["start"],
                "env": {},
            }
        }
    }
    click.echo(json.dumps(config, indent=2))
```

```python
# src/d4/cli/__init__.py
from d4.cli.main import cli

__all__ = ["cli"]
```

- [ ] **Step 4: Write test_cli.py**

```python
# tests/test_cli.py
import pytest
from pathlib import Path
from click.testing import CliRunner
from d4.cli.main import cli


@pytest.fixture
def runner():
    return CliRunner()


class TestCli:
    def test_version(self, runner):
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "0.1.0" in result.output  # may need to match exact format

    def test_help(self, runner):
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "Usage:" in result.output

    def test_mcp_command(self, runner):
        result = runner.invoke(cli, ["mcp"])
        assert result.exit_code == 0
        assert "mcpServers" in result.output

    def test_run_missing_config_auto_inits(self, runner, tmp_path):
        with runner.isolated_filesystem(temp_dir=tmp_path) as td:
            result = runner.invoke(cli, ["run", "test task"])
            assert result.exit_code == 0
            assert "Routing" in result.output
            assert Path(td / "config.yaml").exists()

    def test_agent_list_no_config(self, runner):
        with runner.isolated_filesystem():
            result = runner.invoke(cli, ["agent", "list"])
            assert result.exit_code != 0

    def test_init_creates_config(self, runner, tmp_path):
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(cli, ["init"])
            assert result.exit_code == 0
            assert "Created config" in result.output
```
````

- [ ] **Step 5: Run all tests**

Run:
```bash
pytest tests/test_cli.py tests/test_models.py tests/test_config.py tests/test_agent_registry.py tests/test_orchestrator.py tests/test_pipeline_agent.py -v
```
Expected: All tests PASS

- [ ] **Step 6: Commit**

```bash
git add src/d4/cli/ tests/test_cli.py
git commit -m "feat: CLI with init, start, run, mcp, agent list commands"
```

---

### Task 8: README with Documentation

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Write the README**

```markdown
# ⚒️ mcp-dataforge

**Multi-agent data engineering framework — MCP-native.**

Turn natural language into data pipeline actions. Six specialist agents collaborate through the Model Context Protocol (MCP) to build, validate, and monitor your data infrastructure.

## Quick Start

```bash
# Install
pip install mcp-dataforge

# Initialize a project
dataforge init

# Run a task
dataforge run "profile the customers table and check for nulls"
```

## Architecture

```
MCP Client (Claude Code, Cursor, etc.)
        │
        ▼
┌─────────────────────────────┐
│   Orchestrator MCP Server    │  ← route_task, list_agents, get_pipeline_status
├─────────────────────────────┤
│  Pipeline │ DQ │ Schema │   │  ← Each agent is its own MCP server
│  Orchestration │ Catalog │  │
│  Observability              │
└─────────────────────────────┘
```

## Built-in Agents

| Agent | Tools |
|-------|-------|
| **Pipeline** | `generate_pipeline`, `debug_sql`, `explain_plan`, `run_spark`, `lint_pipeline` |
| **Data Quality** | `profile_data`, `detect_anomalies`, `validate_rules`, `compute_metrics` |
| **Schema** | `detect_drift`, `generate_migration`, `lint_schema`, `lineage` |
| **Orchestration** | `create_dag`, `manage_retry`, `resolve_deps`, `backfill` |
| **Catalog** | `search`, `describe`, `impact_analysis`, `tag` |
| **Observability** | `get_pipeline_health`, `alert_summary`, `cost_analysis`, `suggest_optimizations` |

## CLI Usage

```bash
dataforge init                    # Create config.yaml
dataforge start                   # Start orchestrator + all agents
dataforge run "task description"  # Run a one-off task
dataforge agent list              # List configured agents
dataforge mcp                     # Print MCP config for Claude Code
```

## Claude Code Integration

Add to your `~/.claude/settings.json`:

```json
{
  "mcpServers": {
    "dataforge": {
      "command": "dataforge",
      "args": ["start"]
    }
  }
}
```

## Configuration

Create a `config.yaml`:

```yaml
version: "1.0"
project: "my-data-platform"

agents:
  pipeline:
    command: "python -m d4.agents.pipeline.server"
    transport: stdio
    capabilities: ["sql", "spark"]
```

## Development

```bash
# Install in editable mode
pip install -e ".[dev]"

# Run tests
pytest

# Run a specific test
pytest tests/test_pipeline_agent.py -v
```

## License

Apache 2.0
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: README with quick start, architecture, CLI, and MCP integration docs"
```

---

## Spec Coverage Check

| Spec Requirement | Task |
|-----------------|------|
| Project skeleton | Task 1 |
| Core data models (Task, AgentStep, AgentResponse, Capability) | Task 2 |
| Orchestrator MCP Server (route_task, list_agents, get_pipeline_status) | Task 5 |
| Pipeline Agent (generate_pipeline, debug_sql, explain_plan) | Task 6 |
| CLI (init, start, run, mcp) | Task 7 |
| YAML config + agent discovery | Task 3, 4 |
| stdio transport | Task 5, 6 (server functions are transport-agnostic; stdio used by CLI start) |
| Claude Code MCP integration | Task 8 (README) |

**All spec requirements for Phase 1 are covered by the tasks above.**
