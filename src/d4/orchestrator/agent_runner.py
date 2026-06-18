"""Agent runner — launch individual agent MCP servers for SSE deployment."""
import sys
import click

AGENTS = {
    "pipeline": "d4.agents.pipeline.server_sse",
    "dq": "d4.agents.dq.server_sse",
    "schema": "d4.agents.schema.server_sse",
    "catalog": "d4.agents.catalog.server_sse",
    "observability": "d4.agents.observability.server_sse",
    "orchestration": "d4.agents.orchestration.server_sse",
    "orchestrator": "d4.orchestrator.mcp_server",
}


@click.command()
@click.argument("name", type=click.Choice(list(AGENTS.keys())))
@click.option("--transport", default="sse", type=click.Choice(["stdio", "sse"]))
@click.option("--port", default=None, type=int, help="Port for SSE transport")
@click.option("--host", default="0.0.0.0", help="Host for SSE transport")
def agent(name, transport, port, host):
    """Run a single agent as an MCP server."""
    import importlib

    module = importlib.import_module(AGENTS[name])
    if hasattr(module, "run"):
        click.echo(f"Starting {name} agent ({transport})...", err=True)
        module.run(
            transport=transport,
            port=port or (9000 + list(AGENTS.keys()).index(name)),
        )
    else:
        click.echo(f"Starting {name} orchestrator ({transport})...", err=True)
        from d4.orchestrator.mcp_server import mcp

        kwargs = {}
        if transport == "sse":
            kwargs["port"] = port or 8080
        mcp.run(transport=transport, **kwargs)


if __name__ == "__main__":
    agent()
