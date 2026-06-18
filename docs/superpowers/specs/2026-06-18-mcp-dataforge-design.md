# mcp-dataforge: Multi-Agent Data Engineering Framework

**Date:** 2026-06-18
**Status:** Draft

## Overview

mcp-dataforge is an MCP-native, multi-agent framework specialized for data engineering. It enables natural language-driven data pipeline management through collaboration between specialist agents, each exposed as an MCP (Model Context Protocol) server.

Six specialist agents work together — Pipeline, Data Quality, Schema, Orchestration, Catalog, and Observability — orchestrated by a central Router Agent. The framework is designed for extensibility: anyone can add new agent plugins as MCP servers.

---

## Architecture

### Multi-Agent Collaboration Model

```
MCP Client (Claude Code, Cursor, VS Code, Web UI, CLI)
        │
        │ MCP Protocol (stdio / SSE)
        ▼
┌─────────────────────────────────────────────┐
│         Orchestrator MCP Server              │
│  ┌─────────┬──────────────┬────────────────┐ │
│  │ Router  │ Task Planner │ Agent Gateway  │ │
│  └─────────┴──────────────┴────────────────┘ │
└─────────────────────────────────────────────┘
        │
        ├── Pipeline MCP Server  (tools: generate_pipeline, debug_sql, ...)
        ├── DQ MCP Server       (tools: profile_data, detect_anomalies, ...)
        ├── Schema MCP Server   (tools: detect_drift, generate_migration, ...)
        ├── Orchestration MCP Server (tools: create_dag, manage_retry, ...)
        ├── Catalog MCP Server  (tools: search, describe, impact_analysis, ...)
        └── Observability MCP Server (tools: get_pipeline_health, cost_analysis, ...)
```

### Task Lifecycle

```
User → Router: task description
  → Parse intent → Resolve plan → Delegate agents
  → Execute (sequential/parallel/debate)
  → Synthesize results → Present to user
```

### Collaboration Patterns

| Pattern | Description | Use Case |
|---------|-------------|----------|
| **Sequential** | Output A → Input B → Input C | Pipeline → Schema → DQ |
| **Parallel** | Fan-out to multiple agents | Audit: all agents check independently |
| **Debate** | Review & validate across agents | Consensus before destructive action |

### Context Passing

Agents communicate through the Orchestrator via MCP tool calls. Each response carries:

- `session_id` — for multi-step context tracking
- `context` — shared data across agents
- `artifacts` — output files, reports, schema diffs
- `confidence` — score (0-1) for weighted decision making
- `requires_approval` — flag for human-in-the-loop gate

---

## Core Components

### 1. Orchestrator MCP Server

The entry point. Single MCP server that clients connect to.

**Tools:**
- `route_task(task, context?)` — parse intent, plan multi-agent execution, orchestrate & return result
- `list_agents()` — discover available agents and their capabilities
- `get_pipeline_status(pipeline_id)` — track progress of running pipelines

**Agent Discovery:**
- Config-based: YAML file listing agent commands
- Auto-discover: scan package entry_points (for third-party plugins)

### 2. Specialist Agents

Each agent is a standalone MCP server with a set of tools.

| Agent | Tools | Integrations |
|-------|-------|-------------|
| **Pipeline** | `generate_pipeline`, `debug_sql`, `run_spark`, `explain_plan`, `lint_pipeline` | Snowflake, BigQuery, Redshift, Spark, dbt |
| **Data Quality** | `profile_data`, `detect_anomalies`, `validate_rules`, `compute_metrics` | Sampling-based profiling, auto-generate dbt tests |
| **Schema** | `detect_drift`, `generate_migration`, `lint_schema`, `lineage` | Column-level lineage, schema contracts |
| **Orchestration** | `create_dag`, `manage_retry`, `resolve_deps`, `backfill` | Airflow, Dagster, Prefect |
| **Catalog** | `search`, `describe`, `impact_analysis`, `tag` | DataHub, OpenMetadata, SQLite |
| **Observability** | `get_pipeline_health`, `alert_summary`, `cost_analysis`, `suggest_optimizations` | Prometheus, Grafana, Datadog |

### 3. Data Models (Pydantic)

```
Task        → id, description, context, session_id, agent_plan
AgentStep   → agent, tool, params, depends_on, parallel
AgentResponse → status, summary, confidence, artifacts, requires_approval, error
Capability  → name, version, tools
```

---

## A2A Communication

- **Transport:** stdio (local development) / SSE (production/remote)
- **Protocol:** MCP tool calls via Orchestrator proxy
- **Patterns:** Direct call (sequential), Broadcast (fan-out), Agent-to-Agent (forward via proxy)
- **Human-in-the-Loop:** Any tool call can flag `requires_approval`. Orchestrator pauses, asks user, resumes.

### Error Handling

- Agent-level retry (3×, exponential backoff)
- Graceful degradation (agent down → reduced capability, not total failure)
- Circuit breaker (repeated failures → temporary cooldown)

---

## Security

- **Tool-level RBAC:** `read` (safe) vs `write` (requires approval) permissions
- **Dry-run mode:** All destructive operations preview before execution
- **Audit trail:** Every tool call, decision, and approval logged
- **Credential isolation:** Each agent has its own credential scope

---

## Configuration

```yaml
# ~/.dataforge/config.yaml
version: "1.0"
project: "my-data-platform"

agents:
  pipeline:
    command: "python -m d4.agents.pipeline"
    transport: stdio
    capabilities: ["sql", "spark", "dbt"]
  dq:
    command: "python -m d4.agents.dq"
    transport: stdio

integrations:
  warehouse: snowflake
    target: prod
```

### CLI Commands

```
dataforge init                    # Create config.yaml
dataforge start                   # Start all agents
dataforge agent list              # List available agents
dataforge plugin install <name>   # Install plugin
dataforge run "task description"  # Run one-off task
dataforge mcp                     # Run as MCP server (for client config)
```

---

## Packaging & Distribution

- `pip install mcp-dataforge` — core + all built-in agents
- `pip install d4-agent-*` — optional agent plugins
- Docker images per agent for SSE/remote deployment
- Homebrew for macOS users

### MCP Client Integration (Claude Code)

```json
{
  "mcpServers": {
    "dataforge": {
      "command": "dataforge",
      "args": ["mcp"]
    }
  }
}
```

---

## Testing Strategy

| Level | Scope |
|-------|-------|
| **Unit** | Agent logic, model validation, tool execution (mocked MCP) |
| **Integration** | Agent-to-agent communication, routing, context passing |
| **E2E** | Full pipeline: user request → orchestration → multi-agent → result (DuckDB/SQLite) |

---

## Roadmap

### Phase 1 — Core Foundation (🎯)
- [x] Design complete
- [ ] Orchestrator MCP server skeleton
- [ ] Pipeline Agent (SQL-focused: generate, debug, explain)
- [ ] CLI: `init | start | run | mcp`
- [ ] YAML config + agent discovery
- [ ] stdio transport
- [ ] Claude Code MCP integration

### Phase 2 — Agent Expansion (🚀)
- [ ] Data Quality Agent
- [ ] Schema Agent
- [ ] A2A patterns: sequential, parallel, debate
- [ ] SSE transport for remote deployment

### Phase 3 — Ecosystem (🌐)
- [ ] Orchestration, Catalog, Observability agents
- [ ] Docker deployment
- [ ] Plugin API documentation
- [ ] Third-party plugin support

### Phase 4 — Enterprise (🏢)
- [ ] RBAC with audit trail
- [ ] SSO integration
- [ ] Team collaboration features
- [ ] Web UI

---

## Design Principles

1. **MCP-native** — Every agent is an MCP server. No custom protocols.
2. **Plugin by design** — Extend via installable MCP server packages.
3. **Tool-first** — Agents execute real tools, not just chat.
4. **Human-in-the-loop** — All destructive actions require approval.
5. **Graceful degradation** — Partial agent availability = partial capability, not failure.
6. **Observable by default** — Every action traceable, every decision auditable.
