"""Orchestration Agent — DAG management, scheduling, retry, backfill."""

from datetime import datetime, timedelta

_STORE: dict = {
    "dags": {},
    "runs": [],
}


def _ensure_dag(dag_id: str) -> dict:
    if dag_id not in _STORE["dags"]:
        _STORE["dags"][dag_id] = {
            "dag_id": dag_id,
            "description": "",
            "tasks": [],
            "schedule": None,
            "is_active": True,
            "created_at": "2026-06-18T00:00:00",
        }
    return _STORE["dags"][dag_id]


def create_dag(
    dag_id: str,
    description: str = "",
    schedule: str | None = None,
    tasks: list[dict] | None = None,
) -> dict:
    """Create a DAG with tasks and dependencies.

    Each task: {"id": str, "command": str, "depends_on": list[str], "timeout_min": int, "retries": int}
    """
    if dag_id in _STORE["dags"]:
        return {"status": "error", "message": f"DAG '{dag_id}' already exists"}

    if tasks is None:
        tasks = []

    # Validate dependencies
    task_ids = {t["id"] for t in tasks}
    for t in tasks:
        for dep in t.get("depends_on", []):
            if dep not in task_ids:
                return {
                    "status": "error",
                    "message": f"Task '{t['id']}' depends on '{dep}' which doesn't exist",
                }

    # Detect cycles (simple: check if any task transitively depends on itself)
    dep_map = {t["id"]: t.get("depends_on", []) for t in tasks}
    for task_id in task_ids:
        visited = set()
        queue = list(dep_map[task_id])
        while queue:
            current = queue.pop(0)
            if current == task_id:
                return {
                    "status": "error",
                    "message": f"Circular dependency detected involving task '{task_id}'",
                }
            if current not in visited:
                visited.add(current)
                queue.extend(dep_map.get(current, []))

    # Compute topological order
    in_degree = {t["id"]: 0 for t in tasks}
    for t in tasks:
        for dep in t.get("depends_on", []):
            in_degree[t["id"]] = in_degree.get(t["id"], 0) + 1

    queue = [tid for tid, deg in in_degree.items() if deg == 0]
    topo_order = []
    while queue:
        node = queue.pop(0)
        topo_order.append(node)
        for t in tasks:
            if node in t.get("depends_on", []):
                in_degree[t["id"]] -= 1
                if in_degree[t["id"]] == 0:
                    queue.append(t["id"])

    dag = _ensure_dag(dag_id)
    dag["description"] = description
    dag["schedule"] = schedule
    dag["tasks"] = tasks

    return {
        "status": "success",
        "dag_id": dag_id,
        "description": description,
        "schedule": schedule,
        "task_count": len(tasks),
        "topological_order": topo_order,
    }


def manage_retry(dag_id: str, task_id: str, action: str = "retry", max_retries: int = 3) -> dict:
    """Manage retry configuration for a specific task in a DAG.

    action: "retry" (trigger retry), "configure" (update settings), "skip" (skip task)
    """
    dag = _STORE["dags"].get(dag_id)
    if not dag:
        return {"status": "error", "message": f"DAG '{dag_id}' not found"}

    task = None
    for t in dag.get("tasks", []):
        if t["id"] == task_id:
            task = t
            break

    if not task:
        return {"status": "error", "message": f"Task '{task_id}' not found in DAG '{dag_id}'"}

    if action == "retry":
        task["retries"] = task.get("retries", 0) + 1
        task["max_retries"] = max_retries
        return {
            "status": "success",
            "dag_id": dag_id,
            "task_id": task_id,
            "action": "retry_triggered",
            "retry_count": task["retries"],
            "max_retries": max_retries,
        }

    elif action == "configure":
        task["max_retries"] = max_retries
        task["retries"] = 0  # Reset retry count
        return {
            "status": "success",
            "dag_id": dag_id,
            "task_id": task_id,
            "action": "configured",
            "max_retries": max_retries,
        }

    elif action == "skip":
        task["skipped"] = True
        return {
            "status": "success",
            "dag_id": dag_id,
            "task_id": task_id,
            "action": "skipped",
        }

    return {"status": "error", "message": f"Unknown action: {action}"}


def resolve_deps(dag_id: str) -> dict:
    """Resolve and display task dependencies for a DAG.

    Returns dependency tree, critical path, and parallelizable groups.
    """
    dag = _STORE["dags"].get(dag_id)
    if not dag:
        return {"status": "error", "message": f"DAG '{dag_id}' not found"}

    tasks = dag.get("tasks", [])
    if not tasks:
        return {"dag_id": dag_id, "task_count": 0, "dependency_tree": []}

    # Build dependency info
    dep_map = {}
    for t in tasks:
        tid = t["id"]
        deps = t.get("depends_on", [])
        dep_map[tid] = {
            "id": tid,
            "depends_on": deps,
            "depended_by": [],
        }

    for t in tasks:
        for dep in t.get("depends_on", []):
            if dep in dep_map:
                dep_map[dep]["depended_by"].append(t["id"])

    # Build levels (parallel groups)
    in_degree = {t["id"]: len(t.get("depends_on", [])) for t in tasks}
    levels = []
    remaining = set(in_degree.keys())

    while remaining:
        current_level = [tid for tid in remaining if in_degree[tid] == 0]
        if not current_level:
            break  # Cycle or remaining deps not satisfied
        levels.append(current_level)
        for tid in current_level:
            remaining.remove(tid)
            for t in tasks:
                if tid in t.get("depends_on", []):
                    in_degree[t["id"]] -= 1

    # Critical path (longest chain from root to leaf)
    task_depths = {}
    task_predecessor = {}
    for level in levels:
        for tid in level:
            deps = dep_map[tid]["depends_on"]
            if not deps:
                task_depths[tid] = 1
                task_predecessor[tid] = None
            else:
                pred = max(deps, key=lambda d: task_depths.get(d, 0))
                task_depths[tid] = task_depths.get(pred, 0) + 1
                task_predecessor[tid] = pred

    max_depth = max(task_depths.values()) if task_depths else 0
    deepest = [tid for tid, depth in task_depths.items() if depth == max_depth][0]
    # Trace back from deepest leaf to root
    critical_path = []
    node = deepest
    while node is not None:
        critical_path.insert(0, node)
        node = task_predecessor.get(node)

    # Build dependency tree
    root_tasks = [tid for tid, info in dep_map.items() if not info["depends_on"]]

    def build_tree(node_id: str, visited: set = None) -> dict:
        if visited is None:
            visited = set()
        if node_id in visited:
            return {"id": node_id, "children": []}
        visited.add(node_id)
        children = [build_tree(dep, visited) for dep in dep_map[node_id]["depended_by"]]
        return {"id": node_id, "children": children}

    dependency_tree = [build_tree(root) for root in root_tasks]

    return {
        "dag_id": dag_id,
        "task_count": len(tasks),
        "levels": levels,
        "critical_path": critical_path,
        "critical_path_length": max_depth,
        "can_parallelize": any(len(level) > 1 for level in levels),
        "dependency_tree": dependency_tree,
    }


def backfill(dag_id: str, start_date: str, end_date: str, dry_run: bool = True) -> dict:
    """Plan or execute a backfill for a date range.

    If dry_run=True, returns the plan without executing.
    """
    dag = _STORE["dags"].get(dag_id)
    if not dag:
        return {"status": "error", "message": f"DAG '{dag_id}' not found"}

    # Parse dates and calculate intervals
    try:
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
    except ValueError:
        return {"status": "error", "message": "Dates must be in YYYY-MM-DD format"}

    if end < start:
        return {"status": "error", "message": "end_date must be after start_date"}

    # Generate schedule intervals based on DAG schedule
    schedule = dag.get("schedule", "@daily")
    if schedule == "@daily":
        delta = timedelta(days=1)
    elif schedule == "@hourly":
        delta = timedelta(hours=1)
    elif schedule == "@weekly":
        delta = timedelta(weeks=1)
    elif schedule == "@monthly":
        # Approximate monthly as 30 days
        delta = timedelta(days=30)
    else:
        delta = timedelta(days=1)

    intervals = []
    current = start
    while current <= end:
        intervals.append(current.strftime("%Y-%m-%d"))
        current += delta

    total_runs = len(intervals) * len(dag.get("tasks", []))

    if dry_run:
        return {
            "status": "planned",
            "dag_id": dag_id,
            "start_date": start_date,
            "end_date": end_date,
            "schedule": schedule,
            "total_intervals": len(intervals),
            "tasks_per_run": len(dag.get("tasks", [])),
            "total_task_runs": total_runs,
            "intervals": intervals[:10],  # Show first 10
            "note": f"Run with dry_run=False to execute {total_runs} task runs across {len(intervals)} intervals",
        }

    # Execute (record runs)
    execution_runs = []
    for interval in intervals:
        for task in dag.get("tasks", []):
            run = {
                "dag_id": dag_id,
                "task_id": task["id"],
                "interval": interval,
                "status": "queued",
            }
            _STORE["runs"].append(run)
            execution_runs.append(run)

    return {
        "status": "executed",
        "dag_id": dag_id,
        "start_date": start_date,
        "end_date": end_date,
        "total_runs": len(execution_runs),
        "queued_runs": len(execution_runs),
    }
