"""Interactive chat mode for DataForge CLI with rich formatting."""
import sys
import shutil
from pathlib import Path
from d4.config.loader import find_config, load_config, write_default_config
from d4.registry.agent_registry import AgentRegistry
from d4.orchestrator.server import Orchestrator


def _print_banner(text: str, char: str = "═", width: int | None = None) -> None:
    """Print a centered banner line."""
    if width is None:
        width = min(shutil.get_terminal_size().columns, 60)
    side = (width - len(text) - 2) // 2
    print(f"{char * side} {text} {char * side}")


def _print_table(rows: list[list[str]], header: list[str] | None = None) -> None:
    """Print a simple aligned table."""
    if not rows:
        return
    cols = len(rows[0])
    widths = [max(len(str(r[i])) for r in rows) for i in range(cols)]
    if header:
        widths = [max(widths[i], len(header[i])) for i in range(cols)]
        hdr = "  ".join(h.ljust(widths[i]) for i, h in enumerate(header))
        print(f"  {hdr}")
        print(f"  {'─' * sum(widths) + '─' * (cols * 2)}")
    for row in rows:
        line = "  ".join(str(row[i]).ljust(widths[i]) for i in range(cols))
        print(f"  {line}")


def _summarize_result(r2: dict) -> str:
    """Generate a concise one-line summary from an agent result."""
    if not isinstance(r2, dict):
        return ""
    if r2.get("error"):
        return f"❌ {r2['error'][:60]}"
    if "row_count" in r2:
        cols = len(r2.get("columns", []))
        return f"📊 {r2['row_count']:,} rows, {cols} columns"
    if r2.get("has_drift") is not None:
        added = len(r2.get("added", []))
        removed = len(r2.get("removed", []))
        modified = len(r2.get("modified", []))
        parts = []
        if added: parts.append(f"+{added} added")
        if removed: parts.append(f"-{removed} removed")
        if modified: parts.append(f"~{modified} modified")
        drift = "yes" if r2["has_drift"] else "no"
        return f"📐 Drift: {drift}" + (f" ({', '.join(parts)})" if parts else "")
    if "total_rules" in r2:
        passed = r2.get("passed", 0)
        total = r2.get("total_rules", 0)
        rate = r2.get("pass_rate", 0) * 100
        return f"✅ Rules: {passed}/{total} passed ({rate:.0f}%)"
    if "total_results" in r2:
        return f"🔍 {r2['total_results']} results found"
    if r2.get("health"):
        alerts = r2.get("active_alerts", 0)
        rate = r2.get("success_rate", 0) * 100
        al = f", {alerts} alerts" if alerts else ""
        return f"❤️  Health: {r2['health']} ({rate:.0f}% success{al})"
    if "dag_id" in r2 and "topological_order" in r2:
        tasks = r2.get("task_count", 0)
        return f"⚡ DAG created: {tasks} tasks"
    if "mermaid" in r2:
        return f"📊 DAG graph: {r2.get('task_count', '?')} tasks"
    if "total_dags" in r2:
        return f"📋 {r2['total_dags']} DAGs"
    if "statement" in r2.get("type", "") or r2.get("statements"):
        stmts = len(r2.get("statements", []))
        return f"📝 {stmts} migration statements"
    if "monthly_total" in r2:
        return f"💰 ${r2['monthly_total']:,.0f}/mo (savings: ${r2.get('total_potential_savings', 0):,.0f})"
    if "suggestions" in r2:
        return f"💡 {r2['total_suggestions']} optimization suggestions"
    return ""


def _print_result(result: dict) -> None:
    """Print a formatted execution result."""
    icon = "✅" if result["status"] == "completed" else "⚠️"
    print(f"\n  {icon} \033[1mPipeline:\033[0m {result['pipeline_id']}")
    print(f"     \033[1mStatus:\033[0m {result['status']}")

    chain = " → ".join(result.get("pipeline", []))
    if chain:
        print(f"     \033[1mChain:\033[0m {chain}")

    for r in result.get("results", []):
        status = r.get("status", "?")
        agent_name = r.get("agent", "?")
        r2 = r.get("result", {})
        summary = _summarize_result(r2)
        icon = "✅" if status == "success" else "❌"
        line = f"  {icon} \033[1m{agent_name}\033[0m"
        if summary:
            line += f"  {summary}"
        else:
            line += f"  {status}"
        print(line)

    # Show circuit breaker info
    for r in result.get("results", []):
        cb = r.get("circuit_breaker")
        if cb:
            print(f"  ⚠️  \033[33mCircuit breaker: {cb}\033[0m")


def chat_loop():
    """Run an interactive chat session with rich formatting."""
    config_path = find_config()
    if not config_path:
        config_path = Path.cwd() / "config.yaml"
        write_default_config(config_path)
        print(f"  ⚙️  Auto-created config: {config_path}")

    config = load_config(config_path)
    registry = AgentRegistry()
    registry.load_from_config(config)
    orch = Orchestrator(registry=registry)

    agents = registry.list_agents()
    term_width = min(shutil.get_terminal_size().columns, 60)

    print()
    _print_banner("⚒️  DataForge Interactive", "═", term_width)
    print("  Multi-agent data engineering framework")
    print(f"  Agents: {', '.join(a.name for a in agents)}")
    print(f"  Pipelines: {len(orch.pipelines)} tracked")
    _print_banner("", "─", term_width)
    print("  \033[90mCommands: <task> | agents | pipelines | status <id> | help | exit\033[0m")
    _print_banner("", "─", term_width)
    print()

    while True:
        try:
            raw = input("\033[36mdataforge>\033[0m ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not raw:
            continue
        if raw.lower() in ("exit", "quit", "q"):
            _print_banner("Goodbye! 👋", "═", term_width)
            break

        if raw.lower() in ("help", "?"):
            print()
            _print_table(
                [["<task description>", "Execute a data engineering task"],
                 ["agents", "List all available agents"],
                 ["pipelines", "Show pipeline execution history"],
                 ["status <id>", "Get detailed pipeline status"],
                 ["parallel <task1> | <task2>", "Run two tasks in parallel"],
                 ["help", "Show this help"],
                 ["exit / quit", "Exit interactive mode"]],
                ["Command", "Description"]
            )
            print()
            continue

        if raw.lower() == "agents":
            print()
            _print_table(
                [[a.name, a.transport, ", ".join(a.capabilities[:4])] for a in agents],
                ["Agent", "Transport", "Capabilities"]
            )
            print()
            continue

        if raw.lower() == "pipelines":
            if not orch.pipelines:
                print("  \033[90mNo pipelines yet. Execute a task to get started.\033[0m")
                continue
            print()
            _print_table(
                [[pid[:16], data.get("status", "?"), data.get("task", "")[:50]]
                 for pid, data in list(orch.pipelines.items())[-10:]],
                ["ID", "Status", "Task"]
            )
            if len(orch.pipelines) > 10:
                print(f"  \033[90m... and {len(orch.pipelines) - 10} more\033[0m")
            print()
            continue

        if raw.lower().startswith("status"):
            parts = raw.split()
            pid = parts[1] if len(parts) > 1 else ""
            if not pid:
                print("  \033[33mUsage: status <pipeline_id>\033[0m")
                continue
            status = orch.get_pipeline_status(pid)
            if status.get("status") == "not_found":
                print(f"  \033[33mPipeline '{pid}' not found.\033[0m")
            else:
                print()
                print(f"  \033[1mPipeline:\033[0m {pid}")
                print(f"  \033[1mStatus:\033[0m   {status['status']}")
                print(f"  \033[1mTask:\033[0m     {status['task']}")
                for r in status.get("results", []):
                    icon = "✅" if r.get("status") == "success" else "❌"
                    summary = _summarize_result(r.get("result", {}))
                    agent = r.get("agent", "?")
                    if summary:
                        print(f"  {icon} \033[1m{agent}\033[0m  {summary}")
                    else:
                        print(f"  {icon} \033[1m{agent}\033[0m  {r.get('status', '?')}")
                print()
            continue

        if raw.lower().startswith("parallel"):
            parts = raw[9:].strip()
            if "|" in parts:
                tasks = [t.strip() for t in parts.split("|")]
                print(f"  \033[36m▶ Running {len(tasks)} tasks in parallel...\033[0m")
                steps = [{"agent": orch._route_to_agents(t)[0].name if orch._route_to_agents(t) else "pipeline",
                          "task": t, "context": {}} for t in tasks]
                result = orch.execute_parallel(steps)
                icon = "✅" if result["status"] == "completed" else "⚠️"
                print(f"  {icon} \033[1mParallel:\033[0m {result['total_steps']} tasks, {result['status']}")
                for r in result.get("results", []):
                    if r:
                        summary = _summarize_result(r.get("result", {}))
                        icon = "✅" if r.get("status") == "success" else "❌"
                        agent = r.get("agent", "?")
                        print(f"    {icon} \033[1m{agent}\033[0m  {summary}" if summary else f"    {icon} \033[1m{agent}\033[0m  {r.get('status', '?')}")
            else:
                print("  \033[33mUsage: parallel <task 1> | <task 2> [| <task 3> ...]\033[0m")
            continue

        # Execute as a task
        print(f"  \033[36m▶ {raw}\033[0m")
        result = orch.execute_task(raw)
        _print_result(result)
        print()
