FROM python:3.12-slim

WORKDIR /app

# Install system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy and install package
COPY . .
RUN pip install --no-cache-dir -e ".[dev]"

# Create default config on first run
RUN dataforge init || true

# Expose web UI and SSE ports
EXPOSE 8080

# Default: start MCP server (stdio mode for Claude Code)
CMD ["dataforge", "mcp-server"]
