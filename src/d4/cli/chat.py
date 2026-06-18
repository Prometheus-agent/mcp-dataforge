"""Interactive chat mode for DataForge CLI."""
import sys
from pathlib import Path
from d4.config.loader import find_config, load_config, write_default_config
from d4.registry.agent_registry import AgentRegistry
from d4.orchestrator.server import Orchestrator


def chat_loop():
    """Run an interactive chat session with the orchestrator."""
    # Load or create config
    config_path = find_config()
    if not config_path:
        config_path = Path.cwd() / "config.yaml"
        write_default_config(config_path)
        print(f"⚙️  Auto-created config: {config_path}")

    config = load_config(config_path)
    registry = AgentRegistry()
    registry.load_from_config(config)
    orch = Orchestrator(registry=registry)

    agents = registry.list_agents()
    agent_names = ", ".join(a.name for a in agents)

    print()
    print("╒══════════════════════════════════════════╕")
    print("│        ⚒️  DataForge Interactive Mode     │")
    print("│  Multi-agent data engineering framework  │")
    print("╞══════════════════════════════════════════╡")
    print(f"│  Agents: {agent_names:<37} │")
    print(f"│  Type 'exit' or 'quit' to stop          │")
    print("╘══════════════════════════════════════════╛")
    print()

    while True:
        try:
            task = input("dataforge> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not task:
            continue
        if task.lower() in ("exit", "quit", "q"):
            print("Goodbye!")
            break

        if task.lower() in ("help", "?"):
            print("Commands: <task description> | agents | pipelines | status <id> | exit")
            continue

        if task.lower() == "agents":
            for a in agents:
                caps = ", ".join(a.capabilities) if a.capabilities else "-"
                print(f"  • {a.name:<16} ({a.transport:<5}) {caps}")
            continue

        if task.lower() == "pipelines":
            if not orch.pipelines:
                print("  No pipelines yet.")
                continue
            for pid, data in orch.pipelines.items():
                print(f"  • {pid[:16]}  {data.get('status','?'):<20} {data.get('task','')[:50]}")
            continue

        if task.lower().startswith("status"):
            parts = task.split()
            pid = parts[1] if len(parts) > 1 else ""
            if not pid:
                print("  Usage: status <pipeline_id>")
                continue
            status = orch.get_pipeline_status(pid)
            if status.get("status") == "not_found":
                print(f"  Pipeline '{pid}' not found.")
            else:
                print(f"  Status: {status['status']}")
                print(f"  Task: {status['task']}")
                for r in status.get("results", []):
                    icon = "✅" if r.get("status") == "success" else "❌"
                    print(f"  {icon} {r.get('agent', '?')}: {r.get('status', '?')}")
            continue

        # Execute as a task
        print(f"⏳ Routing: {task}")
        result = orch.execute_task(task)
        status_icon = "✅" if result["status"] == "completed" else "⚠️"
        print(f"{status_icon} Pipeline: {result['pipeline_id']}")
        print(f"   Summary: {result['summary']}")
        chain = " → ".join(result.get("pipeline", []))
        if chain:
            print(f"   Chain: {chain}")
        for r in result.get("results", []):
            agent_name = r.get("agent", "?")
            status = r.get("status", "?")
            r2 = r.get("result", {})
            summary = ""
            if isinstance(r2, dict):
                if "row_count" in r2:
                    summary = f" — {r2['row_count']} rows, {len(r2.get('columns',[]))} columns"
                elif "has_drift" in r2:
                    summary = f" — drift={r2['has_drift']}"
                elif "total_results" in r2:
                    summary = f" — {r2['total_results']} results"
                elif "health" in r2:
                    summary = f" — health={r2['health']}"
                elif "dag_id" in r2:
                    summary = f" — {r2.get('task_count','?')} tasks"
            icon = "✅" if status == "success" else "❌"
            print(f"  {icon} {agent_name}: {status}{summary}")
        print()
