# Contributing to mcp-dataforge

## Getting Started

```bash
git clone git@github.com:Prometheus-agent/mcp-dataforge.git
cd mcp-dataforge
pip install -e ".[dev]"
```

## Development Workflow

1. Create a branch: `git checkout -b feature/your-feature`
2. Write tests first (TDD)
3. Implement your changes
4. Run tests: `python3 -m pytest`
5. Commit: `git commit -m "feat: your feature"`
6. Push: `git push -u origin feature/your-feature`
7. Open a pull request

## Code Style

- Format with Ruff: `ruff check src/ tests/`
- All functions need docstrings
- Use type hints
- Keep functions focused (under 50 lines where possible)
- Use Pydantic for data models

## Testing

- 179+ tests, all must pass before PR
- Write tests for new agent tools
- Test error cases and edge cases
- Use DuckDB in-memory for DQ agent tests

## Adding a New Agent

1. Create `src/d4/agents/<name>/server.py` with an `execute(task, context)` function
2. Create `src/d4/agents/<name>/__init__.py` that exports `execute`
3. Register in `src/d4/orchestrator/server.py` module_map
4. Add to default config in `src/d4/config/loader.py`
5. Add SSE server in `src/d4/agents/<name>/server_sse.py`
6. Write tests in `tests/test_<name>_agent.py`
7. Run full test suite

## Plugin Development

See `docs/guides/creating-a-plugin.md` for building third-party agents.

## License

Apache 2.0
