# mcp-dataforge

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
        |
        v
+-----------------------------+
|   Orchestrator MCP Server    |  route_task, list_agents, get_pipeline_status
+-----------------------------+
|  Pipeline | DQ | Schema |   |  Each agent is its own MCP server
|  Orchestration | Catalog |  |
|  Observability              |
+-----------------------------+
```

## Built-in Agents

| Agent | Tools |
|-------|-------|
| **Pipeline** | `generate_pipeline`, `debug_sql`, `explain_plan` |
| **Data Quality** | `profile_data`, `detect_anomalies`, `validate_rules` |
| **Schema** | `detect_drift`, `generate_migration`, `lint_schema` |
| **Orchestration** | `create_dag`, `manage_retry`, `resolve_deps` |
| **Catalog** | `search`, `describe`, `impact_analysis` |
| **Observability** | `get_pipeline_health`, `alert_summary`, `cost_analysis` |

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
cd /home/dateng6/brain
pip install -e ".[dev]"

# Run tests
python3 -m pytest

# Run a specific test
python3 -m pytest tests/test_pipeline_agent.py -v
```

## License

Apache 2.0
