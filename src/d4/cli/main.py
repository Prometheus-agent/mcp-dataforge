import sys
import json
from pathlib import Path

import click

from d4 import __version__
from d4.config.loader import find_config, load_config, write_default_config
from d4.registry.agent_registry import AgentRegistry
from d4.orchestrator.server import create_orchestrator, route_task, list_agents, get_pipeline_status


@click.group()
@click.version_option(version=__version__, prog_name="dataforge")
def cli():
    """mcp-dataforge: Multi-agent data engineering framework."""


@cli.command()
@click.option("--dir", "-d", default=".", help="Directory to create config in")
def init(dir):
    """Create a default config.yaml in the current directory."""
    target = Path(dir) / "config.yaml"
    if target.exists():
        click.echo(f"Config already exists: {target}", err=True)
        sys.exit(1)
    write_default_config(target)
    click.echo(f"Created config: {target}")
    click.echo("Run 'dataforge start' to launch the orchestrator and agents.")


@cli.command()
@click.argument("task", required=False)
def start(task):
    """Start the orchestrator and all configured agents.

    If TASK is provided, run it as a one-off command and exit.
    """
    config_path = find_config()
    if not config_path:
        click.echo("No config.yaml found. Run 'dataforge init' first.", err=True)
        sys.exit(1)

    config = load_config(config_path)
    registry = AgentRegistry()
    registry.load_from_config(config)
    orchestrator = create_orchestrator(registry=registry)

    agents = registry.list_agents()
    click.echo(f"Loaded {len(agents)} agent(s) from config:")
    for a in agents:
        caps = ", ".join(a.capabilities) if a.capabilities else "none"
        click.echo(f"  - {a.name} ({caps})")

    if task:
        result = route_task(orchestrator, task)
        click.echo("")
        click.echo(f"Pipeline: {result['pipeline_id']}")
        click.echo(f"Summary: {result['summary']}")
        click.echo("Plan:")
        for step in result["plan"]:
            click.echo(f"  -> {step['agent']}: {step['tool']}({step['params']['task'][:50]}...)")
    else:
        click.echo("")
        click.echo("Orchestrator ready. Use 'dataforge run <task>' or add to Claude Code:")
        click.echo('  "mcpServers": { "dataforge": { "command": "dataforge", "args": ["mcp"] } }')


@cli.command()
@click.argument("task")
def run(task):
    """Run a one-off task through the orchestrator."""
    config_path = find_config()
    if not config_path:
        config_path = Path.cwd() / "config.yaml"
        write_default_config(config_path)
        click.echo(f"Auto-created config: {config_path}")

    config = load_config(config_path)
    registry = AgentRegistry()
    registry.load_from_config(config)
    orchestrator = create_orchestrator(registry=registry)

    click.echo(f"Routing: {task}")
    result = route_task(orchestrator, task)

    click.echo(f"  Pipeline: {result['pipeline_id']}")
    click.echo(f"  {result['summary']}")
    click.echo("")
    click.echo("Execution plan:")
    for i, step in enumerate(result["plan"], 1):
        click.echo(f"  {i}. {step['agent']} -> {step['tool']}")


@cli.group()
def agent():
    """Manage agents."""
    pass


@agent.command("list")
def agent_list():
    """List available agents from config."""
    config_path = find_config()
    if not config_path:
        click.echo("No config found. Run 'dataforge init' first.", err=True)
        sys.exit(1)

    config = load_config(config_path)
    registry = AgentRegistry()
    registry.load_from_config(config)
    agents = registry.list_agents()

    if not agents:
        click.echo("No agents configured.")
        return

    click.echo(f"{'Name':<20} {'Transport':<10} {'Capabilities'}")
    click.echo("-" * 60)
    for a in agents:
        caps = ", ".join(a.capabilities) if a.capabilities else "-"
        click.echo(f"{a.name:<20} {a.transport:<10} {caps}")


@cli.command()
@click.option("--transport", default="stdio", type=click.Choice(["stdio", "sse"]))
@click.option("--port", default=8080, help="Port for SSE transport")
def mcp_server(transport, port):
    """Run as MCP server for Claude Code integration."""
    from d4.orchestrator.mcp_server import mcp
    click.echo(f"Starting DataForge MCP server ({transport})...", err=True)
    if transport == "sse":
        click.echo(f"Listening on http://0.0.0.0:{port}", err=True)
    kwargs = {}
    if transport == "sse":
        kwargs["port"] = port
    mcp.run(transport=transport, **kwargs)


@cli.command()
def mcp():
    """Print MCP server config for Claude Code integration."""
    config = {
        "mcpServers": {
            "dataforge": {
                "command": "dataforge",
                "args": ["mcp-server"],
                "env": {},
            }
        }
    }
    click.echo(json.dumps(config, indent=2))
