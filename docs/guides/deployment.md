# Deployment Guide

This guide covers how to deploy mcp-dataforge in production using Docker, Docker Compose, and SSE mode for scaling individual agents.

---

## Quick Start (Single Container)

The simplest way to run the full stack in a single container:

```bash
docker build -t mcp-dataforge .
docker run -d --name dataforge -p 8080:8080 mcp-dataforge dataforge web
```

This starts the web dashboard with all agents loaded in-process. Access it at `http://localhost:8080`.

---

## Multi-Service Deployment (Recommended for Production)

The `docker-compose.yml` provides several deployment profiles:

### Web Dashboard + MCP Server

```bash
# Start everything (web + MCP server in stdio mode)
docker compose up -d web

# Web UI at http://localhost:8080
# API at http://localhost:8080/api/agents
```

### SSE Mode for Remote MCP Clients

```bash
docker compose --profile sse up -d sse
# MCP server on SSE at port 8081
```

### MCP Server for Claude Code

```bash
docker compose --profile mcp up -d mcp-server
# Then configure Claude Code to connect via docker:
# {
#   "mcpServers": {
#     "dataforge": {
#       "command": "docker",
#       "args": ["compose", "--profile", "mcp", "up", "--build", "mcp-server"]
#     }
#   }
# }
```

---

## Production Architecture (SSE Mode with Distributed Agents)

For high-availability deployments, each agent can run as an independent microservice communicating via SSE:

```
                       ┌──────────────┐
                       │  Load        │
                       │  Balancer    │
                       └──────┬───────┘
                              │
              ┌───────────────┴───────────────┐
              │                               │
     ┌────────▼────────┐            ┌─────────▼─────────┐
     │  Orchestrator    │            │  Frontend (Next.js)│
     │  (Port 8080)     │            │  (Port 3000)       │
     └────────┬────────┘            └───────────────────┘
              │
    ┌─────────┼─────────┬──────────┬──────────┬──────────┐
    │         │         │          │          │          │
    ▼         ▼         ▼          ▼          ▼          ▼
┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────────┐
│Pipeline │  DQ  │ │Schema│ │Catalog│ │Observ│ │Orch.    │
│:9001  │ :9002 │ :9003 │ :9004 │ :9005 │ │:9006    │
└──────┘ └──────┘ └──────┘ └──────┘ └──────┘ └──────────┘
```

### Step 1: Configure each agent

```yaml
# docker-compose.prod.yml
version: "3.9"

services:
  # ── Agent Services ──
  agent-pipeline:
    build: .
    command: python -m d4.orchestrator.agent_runner pipeline --transport sse --port 9001
    ports: ["9001:9001"]
    restart: unless-stopped
    networks: [dataforge]

  agent-dq:
    build: .
    command: python -m d4.orchestrator.agent_runner dq --transport sse --port 9002
    ports: ["9002:9002"]
    restart: unless-stopped
    networks: [dataforge]

  agent-schema:
    build: .
    command: python -m d4.orchestrator.agent_runner schema --transport sse --port 9003
    ports: ["9003:9003"]
    restart: unless-stopped
    networks: [dataforge]

  agent-catalog:
    build: .
    command: python -m d4.orchestrator.agent_runner catalog --transport sse --port 9004
    ports: ["9004:9004"]
    restart: unless-stopped
    networks: [dataforge]

  agent-observability:
    build: .
    command: python -m d4.orchestrator.agent_runner observability --transport sse --port 9005
    ports: ["9005:9005"]
    restart: unless-stopped
    networks: [dataforge]

  agent-orchestration:
    build: .
    command: python -m d4.orchestrator.agent_runner orchestration --transport sse --port 9006
    ports: ["9006:9006"]
    restart: unless-stopped
    networks: [dataforge]

  # ── Orchestrator ──
  orchestrator:
    build: .
    command: python -m d4.orchestrator.agent_runner orchestrator --transport sse --port 8080
    ports: ["8080:8080"]
    depends_on:
      - agent-pipeline
      - agent-dq
      - agent-schema
      - agent-catalog
      - agent-observability
      - agent-orchestration
    restart: unless-stopped
    networks: [dataforge]

  # ── Web Dashboard ──
  web:
    build: .
    command: dataforge web --host 0.0.0.0 --port 8080
    ports: ["8081:8080"]
    depends_on: [orchestrator]
    restart: unless-stopped
    networks: [dataforge]

networks:
  dataforge:
    driver: bridge
```

### Step 2: Start all services

```bash
docker compose -f docker-compose.prod.yml up -d
```

---

## Production Hardening

### Resource Limits

```yaml
services:
  agent-pipeline:
    deploy:
      resources:
        limits:
          memory: 512M
        reservations:
          memory: 256M
```

### Health Checks

```yaml
services:
  agent-pipeline:
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:9001/health')"]
      interval: 30s
      timeout: 10s
      retries: 3
```

### Monitoring with Prometheus + Grafana

Add to `docker-compose.prod.yml`:

```yaml
  prometheus:
    image: prom/prometheus
    ports: ["9090:9090"]
    volumes: ["./prometheus.yml:/etc/prometheus/prometheus.yml"]
    networks: [dataforge]

  grafana:
    image: grafana/grafana
    ports: ["3000:3000"]
    networks: [dataforge]
```

---

## Cloud Deployment

### Kubernetes (k8s)

```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: dataforge-orchestrator
spec:
  replicas: 2
  selector:
    matchLabels:
      app: dataforge
  template:
    metadata:
      labels:
        app: dataforge
    spec:
      containers:
      - name: orchestrator
        image: mcp-dataforge:latest
        command: ["python", "-m", "d4.orchestrator.agent_runner", "orchestrator", "--transport", "sse"]
        ports:
        - containerPort: 8080
        env:
        - name: DATAFORGE_DB
          value: ":memory:"
```

### VPS / Single Server

```bash
# Clone, build, and run
git clone git@github.com:Prometheus-agent/mcp-dataforge.git
cd mcp-dataforge
docker compose -f docker-compose.prod.yml up -d

# With Caddy as reverse proxy
# Caddyfile:
# dataforge.example.com {
#   reverse_proxy localhost:8081
# }
```

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATAFORGE_DB` | `:memory:` | DuckDB connection string for DQ agent |
| `DATAFORGE_CONFIG` | `./config.yaml` | Path to config file |

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Agents not connecting | Check SSE port mapping and network config |
| High memory usage | Set resource limits per agent in docker-compose |
| Slow pipeline execution | Review circuit breaker settings in orchestrator |
| Frontend shows no data | Verify web service can reach orchestrator API |
