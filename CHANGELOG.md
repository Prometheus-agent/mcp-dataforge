# Changelog

## 0.1.0 (2026-06-18)

### Initial Release
- 6 specialist agents: Pipeline, Data Quality, Schema, Catalog, Observability, Orchestration
- Orchestrator with FastMCP (stdio + SSE)
- Modes: sequential, parallel, mixed pipeline execution
- CLI: init, start, run, agent list, mcp, mcp-server, web
- Web UI dashboard (Next.js + Tailwind + React Flow)
- Docker deployment (Dockerfile + docker-compose)
- GitHub Actions CI (153 tests, Python 3.11-3.13)
- Plugin SDK for third-party agents
