# ⚒️ mcp-dataforge

**Multi-agent data engineering framework — MCP-native.**

Turn natural language into data pipeline actions. Six specialist agents collaborate through the Model Context Protocol (MCP) to build, validate, and monitor your data infrastructure.

[![Tests](https://img.shields.io/badge/tests-153%20passing-brightgreen)](#)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](#)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue)](#)

---

## Quick Start

```bash
# Install
pip install mcp-dataforge

# Initialize a project
dataforge init

# Run a task
dataforge run "profile the customers table and check for nulls"

# Start the web dashboard
dataforge web
# → http://localhost:8080
```

---

## Architecture

```
MCP Client (Claude Code, Cursor, etc.)
        │
        │ MCP Protocol (stdio)
        ▼
┌─────────────────────────────────────┐
│     Orchestrator MCP Server          │
│  route_task · execute_task           │
│  execute_parallel · execute_mixed    │
│  list_agents · get_pipeline_status   │
├─────────────────────────────────────┤
│                                     │
│  ┌──────┐ ┌──────┐ ┌──────┐        │
│  │Pipeline│ │  DQ  │ │Schema│        │
│  └──────┘ └──────┘ └──────┘        │
│  ┌──────┐ ┌──────┐ ┌──────┐        │
│  │Catalog│ │Observ│ │Orch  │        │
│  └──────┘ └──────┘ └──────┘        │
│                                     │
│  Sequential · Parallel · Mixed      │
└─────────────────────────────────────┘
```

### Execution Modes

| Mode | Description | Example |
|------|-------------|---------|
| **Sequential** | Agents run one after another, context passes between them | Profile → Detect drift → Generate migration |
| **Parallel** | Multiple agents run concurrently, results merged | Scan schema + check health + search catalog |
| **Mixed** | Multi-stage: parallel groups followed by sequential steps | [DQ + Schema] in parallel → Catalog |

---

## Built-in Agents

| Agent | Tools | Description |
|-------|-------|-------------|
| 🔧 **Pipeline** | `generate_pipeline`, `debug_sql`, `explain_plan` | SQL generation, debugging, and optimization |
| ✅ **Data Quality** | `profile_data`, `detect_anomalies`, `validate_rules` | Data profiling, anomaly detection, rule validation |
| 📐 **Schema** | `detect_drift`, `generate_migration`, `lint_schema`, `lineage` | Schema comparison, migration scripts, linting |
| 📚 **Catalog** | `search`, `describe`, `impact_analysis`, `tag` | Data discovery, documentation, change impact |
| 🔍 **Observability** | `get_pipeline_health`, `alert_summary`, `cost_analysis`, `suggest_optimizations` | Pipeline health, alerts, cost optimization |
| ⚡ **Orchestration** | `create_dag`, `manage_retry`, `resolve_deps`, `backfill`, `list_dags`, `pause`, `unpause`, `visualize` | DAG management, scheduling, dependency resolution |

---

## CLI Usage

```bash
# Project setup
dataforge init                    # Create config.yaml
dataforge agent list              # List configured agents

# Execution
dataforge run "task description"  # Run a one-off task
dataforge start                   # Start orchestrator + agents

# Server modes
dataforge mcp-server              # Run as MCP server (stdio)
dataforge mcp-server --transport sse --port 8080  # SSE mode
dataforge mcp                     # Print MCP config for Claude Code

# Web dashboard
dataforge web                     # Start web UI (http://localhost:8080)
dataforge web --port 9000         # Custom port
```

### Run Complex Pipelines

```bash
# Sequential — agents run in order, context flows between them
dataforge run "profile customers table, detect schema drift, and generate migration"

# Multi-agent — single task routed to relevant agents
dataforge run "check data quality and search catalog for PII data"
```

---

## Claude Code Integration

Add to your `~/.claude/settings.json`:

```json
{
  "mcpServers": {
    "dataforge": {
      "command": "dataforge",
      "args": ["mcp-server"]
    }
  }
}
```

Then from Claude Code:

```
route_task("check null rates in orders table")
→ Returns execution plan with 1 agent (dq)

execute_task("profile customers and fix schema drift")
→ Auto-routes to DQ + Schema agents, runs sequentially, returns results

execute_parallel({"steps": [
  {"agent": "catalog", "task": "search for PII data"},
  {"agent": "observability", "task": "health check"}
]})
→ Both agents run concurrently, results merged

execute_custom_pipeline({"pipeline": [
  {"agent": "dq", "task": "profile orders"},
  {"agent": "schema", "task": "detect drift"}
]})
→ Custom sequential pipeline with context passing
```

---

## Web Dashboard

Start the dashboard to monitor pipelines, agents, and execution history:

```bash
dataforge web
# Open http://localhost:8080
```

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/agents` | GET | List all agents with capabilities |
| `/api/pipelines` | GET | List all tracked pipelines |
| `/api/pipelines/{id}` | GET | Get pipeline status |
| `/api/execute` | POST | Execute a task |
| `/api/pipeline/parallel` | POST | Run parallel pipeline |
| `/api/pipeline/custom` | POST | Run custom sequential pipeline |
| `/api/pipeline/mixed` | POST | Run mixed (parallel + sequential) pipeline |

---

## Configuration

```yaml
# config.yaml
version: "1.0"
project: "my-data-platform"

agents:
  pipeline:
    command: "python -m d4.agents.pipeline.server"
    transport: stdio
    capabilities: ["sql", "spark"]
  dq:
    command: "python -m d4.agents.dq.server"
    transport: stdio
    capabilities: ["data_quality", "profiling", "validation"]
  schema:
    command: "python -m d4.agents.schema.server"
    transport: stdio
    capabilities: ["schema", "drift", "migration", "lineage"]
  catalog:
    command: "python -m d4.agents.catalog.server"
    transport: stdio
    capabilities: ["catalog", "discovery", "documentation", "tagging"]
  observability:
    command: "python -m d4.agents.observability.server"
    transport: stdio
    capabilities: ["observability", "monitoring", "alerts", "cost"]
  orchestration:
    command: "python -m d4.agents.orchestration.server"
    transport: stdio
    capabilities: ["orchestration", "dag", "scheduling", "backfill"]
```

---

## Development

```bash
# Clone and install
git clone git@github.com:Prometheus-agent/mcp-dataforge.git
cd mcp-dataforge
pip install -e ".[dev]"

# Run tests (153+ tests)
python3 -m pytest

# Run specific test file
python3 -m pytest tests/test_orchestrator.py -v

# Run the MCP server locally
dataforge mcp-server

# Run the web dashboard
dataforge web
```

### Project Structure

```
src/d4/
├── agents/
│   ├── pipeline/         # SQL pipeline generation
│   ├── dq/               # Data profiling & validation
│   ├── schema/           # Drift detection & migration
│   ├── catalog/          # Data discovery & docs
│   ├── observability/    # Health & cost monitoring
│   └── orchestration/    # DAG management & scheduling
├── config/               # YAML config loader
├── registry/             # Agent registry & discovery
├── orchestrator/         # Core orchestrator + MCP server
├── web/                  # FastAPI web dashboard
├── cli/                  # Click CLI
└── models/               # Pydantic data models
tests/                    # 153+ tests across all modules
```

---

## Roadmap

### Phase 1 — Core Foundation ✅
- [x] 6 specialist agents with 22+ tools
- [x] Orchestrator MCP server (stdio + SSE)
- [x] CLI with init, run, agent, mcp commands
- [x] Sequential, parallel, mixed pipeline execution
- [x] FastAPI web dashboard
- [x] 153+ tests, 100% passing

### Phase 2 — Agent Expansion 🚧
- [ ] Data Quality agent with DuckDB profiling
- [ ] Schema agent with migration generation
- [ ] Catalog agent with impact analysis

### Phase 3 — Ecosystem 🌐
- [ ] Docker deployment
- [ ] Plugin API documentation
- [ ] Third-party plugin support

---

## License

Apache 2.0. See [LICENSE](LICENSE).
