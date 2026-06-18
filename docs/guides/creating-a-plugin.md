# Creating a DataForge Plugin

DataForge uses a plugin architecture where any agent is an MCP server with an `execute()` entry point.

## Quick Start

1. Copy the template: `cp -r templates/d4-plugin d4-plugin-my-agent`
2. Rename `<name>` to your agent name in all files
3. Implement your tools in `server.py`
4. Install: `pip install -e .`
5. Add to `config.yaml`

## Requirements

Every plugin MUST:

1. **Export `execute(task: str, context: dict) -> dict`** — this is what the orchestrator calls
2. **Be a valid MCP server** — the orchestrator can also run it standalone
3. **Return serializable dicts** — results must be JSON-serializable

## Example

See `templates/d4-plugin/` for a complete working example.

## Publishing

```bash
pip install build twine
python -m build
twine upload dist/*
```
