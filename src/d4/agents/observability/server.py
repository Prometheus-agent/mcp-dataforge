"""Observability Agent — pipeline health, alerts, cost analysis, optimization."""


def execute(task: str, context: dict) -> dict:
    """Main entry point — called by orchestrator."""
    task_lower = task.lower()
    if "health" in task_lower:
        return get_pipeline_health(context.get("pipeline", "default"))
    if "alert" in task_lower:
        return alert_summary(
            context.get("severity", "all"),
            context.get("hours", 24),
        )
    if "cost" in task_lower:
        return cost_analysis(
            context.get("provider", "all"),
            context.get("timeframe", "monthly"),
        )
    if "optimize" in task_lower or "suggest" in task_lower:
        return suggest_optimizations(context.get("pipeline", "default"))
    return get_pipeline_health(context.get("pipeline", "default"))


_STORE: dict = {
    "pipelines": {},
    "alerts": [],
    "costs": {},
    "runs": [],
}


def _ensure_pipeline(name: str) -> dict:
    if name not in _STORE["pipelines"]:
        _STORE["pipelines"][name] = {
            "name": name,
            "status": "unknown",
            "last_run": None,
            "success_rate": 1.0,
            "avg_duration_min": 0,
        }
    return _STORE["pipelines"][name]


def record_run(pipeline: str, status: str, duration_min: float, rows_processed: int = 0) -> dict:
    """Record a pipeline run (for seeding test data or logging)."""
    _ensure_pipeline(pipeline)
    run = {
        "pipeline": pipeline,
        "status": status,
        "duration_min": duration_min,
        "rows_processed": rows_processed,
        "timestamp": "2026-06-18T12:00:00",
    }
    _STORE["runs"].append(run)

    # Update pipeline stats
    pip = _STORE["pipelines"][pipeline]
    pip["last_run"] = run["timestamp"]
    pip["status"] = status
    recent = [r for r in _STORE["runs"] if r["pipeline"] == pipeline][-20:]
    successes = sum(1 for r in recent if r["status"] == "success")
    pip["success_rate"] = round(successes / len(recent), 2) if recent else 1.0
    pip["avg_duration_min"] = round(
        sum(r["duration_min"] for r in recent) / len(recent), 1
    ) if recent else 0

    return run


def record_alert(pipeline: str, severity: str, message: str) -> dict:
    """Record an alert (for seeding test data)."""
    alert = {
        "id": f"alert_{len(_STORE['alerts']) + 1}",
        "pipeline": pipeline,
        "severity": severity,
        "message": message,
        "timestamp": "2026-06-18T12:00:00",
        "acknowledged": False,
    }
    _STORE["alerts"].append(alert)
    return alert


def get_pipeline_health(pipeline: str) -> dict:
    """Get health status for a pipeline: status, success rate, last run, recent failures."""
    pip = _ensure_pipeline(pipeline)
    recent_runs = [r for r in _STORE["runs"] if r["pipeline"] == pipeline][-10:]
    recent_alerts = [a for a in _STORE["alerts"] if a["pipeline"] == pipeline][-10:]

    # Determine health status
    if pip["success_rate"] >= 0.95:
        health = "healthy"
    elif pip["success_rate"] >= 0.80:
        health = "degraded"
    else:
        health = "unhealthy"

    return {
        "pipeline": pipeline,
        "health": health,
        "status": pip["status"],
        "success_rate": pip["success_rate"],
        "avg_duration_min": pip["avg_duration_min"],
        "last_run": pip["last_run"],
        "recent_runs": len(recent_runs),
        "recent_runs_summary": [
            {"status": r["status"], "duration_min": r["duration_min"]}
            for r in recent_runs[-5:]
        ],
        "active_alerts": len([a for a in recent_alerts if not a["acknowledged"]]),
        "recent_alerts": [
            {"severity": a["severity"], "message": a["message"], "acknowledged": a["acknowledged"]}
            for a in recent_alerts[-3:]
        ],
    }


def alert_summary(severity: str = "all", hours: int = 24) -> dict:
    """Get summary of alerts filtered by severity and time window."""
    filtered = _STORE["alerts"]
    if severity != "all":
        filtered = [a for a in filtered if a["severity"] == severity]

    counts = {"critical": 0, "warning": 0, "info": 0}
    for a in filtered:
        if a["severity"] in counts:
            counts[a["severity"]] += 1

    pipelines_with_alerts = set(a["pipeline"] for a in filtered)
    unacknowledged = [a for a in filtered if not a["acknowledged"]]

    return {
        "time_window_hours": hours,
        "total_alerts": len(filtered),
        "by_severity": counts,
        "pipelines_affected": len(pipelines_with_alerts),
        "unacknowledged_count": len(unacknowledged),
        "top_alerts": sorted(
            [{"pipeline": a["pipeline"], "severity": a["severity"], "message": a["message"][:60]}
             for a in filtered],
            key=lambda x: (0 if x["severity"] == "critical" else 1, 0 if x["severity"] == "warning" else 2)
        )[:5],
        "pipelines": sorted(pipelines_with_alerts),
    }


def cost_analysis(provider: str = "all", timeframe: str = "monthly") -> dict:
    """Analyze warehouse/compute costs and suggest savings."""
    provider_costs = _STORE["costs"] or {
        "snowflake": {"compute": 4500, "storage": 800, "total": 5300},
        "bigquery": {"compute": 3200, "storage": 600, "total": 3800},
        "databricks": {"compute": 6800, "storage": 1200, "total": 8000},
    }

    if provider != "all" and provider in provider_costs:
        costs = {provider: provider_costs[provider]}
    else:
        costs = provider_costs

    total = sum(c["total"] for c in costs.values())
    top_cost = max(costs.items(), key=lambda x: x[1]["total"])

    # Generate savings recommendations
    recommendations = []
    if top_cost[1]["compute"] > top_cost[1]["storage"] * 3:
        recommendations.append({
            "area": "compute_optimization",
            "potential_savings": round(top_cost[1]["compute"] * 0.15),
            "suggestion": f"{top_cost[0]}: Consider auto-scaling or spot instances for non-production workloads",
        })

    total_compute = sum(c["compute"] for c in costs.values())
    if total_compute > 10000:
        recommendations.append({
            "area": "warehouse_sizing",
            "potential_savings": round(total_compute * 0.10),
            "suggestion": "Review warehouse sizing: consider multi-cluster warehouses for concurrent workloads",
        })

    total_storage = sum(c["storage"] for c in costs.values())
    if total_storage > 2000:
        recommendations.append({
            "area": "storage_optimization",
            "potential_savings": round(total_storage * 0.20),
            "suggestion": "Implement data lifecycle policy: auto-archive data not accessed in 90+ days",
        })

    return {
        "timeframe": timeframe,
        "providers": [
            {"name": name, "compute": c["compute"], "storage": c["storage"], "total": c["total"]}
            for name, c in costs.items()
        ],
        "monthly_total": total,
        "top_provider": top_cost[0],
        "recommendations": recommendations,
        "total_potential_savings": sum(r["potential_savings"] for r in recommendations),
    }


def suggest_optimizations(pipeline: str) -> dict:
    """Suggest performance and cost optimizations for a pipeline."""
    pip = _ensure_pipeline(pipeline)
    recent_runs = [r for r in _STORE["runs"] if r["pipeline"] == pipeline][-20:]

    suggestions = []

    # Duration analysis
    if pip["avg_duration_min"] > 30:
        suggestions.append({
            "category": "performance",
            "severity": "high",
            "finding": f"Pipeline averages {pip['avg_duration_min']}min runtime",
            "suggestion": "Consider incremental processing instead of full refresh",
            "estimated_impact": "Could reduce runtime by 40-60%",
        })

    # Success rate analysis
    if pip["success_rate"] < 0.9:
        suggestions.append({
            "category": "reliability",
            "severity": "high",
            "finding": f"Success rate is {pip['success_rate']*100:.0f}%",
            "suggestion": "Add retry logic with exponential backoff for transient failures",
            "estimated_impact": "Could improve success rate to 99%+",
        })

    # Data volume analysis
    if recent_runs:
        avg_rows = sum(r.get("rows_processed", 0) for r in recent_runs) / len(recent_runs)
        if avg_rows > 10_000_000:
            suggestions.append({
                "category": "efficiency",
                "severity": "medium",
                "finding": f"Pipeline processes {avg_rows:,.0f} rows on average",
                "suggestion": "Review partitioning strategy and add predicate pushdown",
                "estimated_impact": "Could reduce data scanned by 30-50%",
            })
        elif avg_rows == 0:
            suggestions.append({
                "category": "monitoring",
                "severity": "low",
                "finding": "Row count not being tracked",
                "suggestion": "Add row count logging to monitor data volume trends",
                "estimated_impact": "Better visibility into pipeline behavior",
            })

    # Inefficiency patterns
    if len(recent_runs) >= 5:
        durations = [r["duration_min"] for r in recent_runs]
        if max(durations) > min(durations) * 3:  # 3x variance
            suggestions.append({
                "category": "consistency",
                "severity": "medium",
                "finding": f"Runtime varies from {min(durations):.0f}-{max(durations):.0f}min ({max(durations)/min(durations):.0f}x)",
                "suggestion": "Investigate root cause of runtime variance: data skew, resource contention, or queuing",
                "estimated_impact": "More predictable SLAs",
            })

    if not suggestions:
        suggestions.append({
            "category": "info",
            "severity": "low",
            "finding": "No optimizations identified",
            "suggestion": "Continue monitoring; pipeline appears healthy",
            "estimated_impact": "-",
        })

    return {
        "pipeline": pipeline,
        "suggestions": suggestions,
        "total_suggestions": len(suggestions),
    }
