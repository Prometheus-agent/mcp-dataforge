# d4-plugin-<name>

A DataForge agent plugin template.

## Setup

```bash
# Rename directory and replace <name> in all files
pip install -e .
```

## Usage

1. Register in your `config.yaml`:
```yaml
agents:
  <name>:
    command: "python -m d4_plugin_<name>.server"
    transport: stdio
    capabilities: ["<capability>"]
```

2. The orchestrator will auto-discover and call your agent via `execute(task, context)`.

## Development

```bash
pip install -e ".[dev]"
pytest
```
