"""Catalog Agent -- data discovery, documentation, impact analysis, tagging."""


def execute(task: str, context: dict) -> dict:
    """Main entry point — called by orchestrator."""
    task_lower = task.lower()
    if "search" in task_lower or "find" in task_lower:
        return search(
            context.get("query", task.replace("search", "").replace("find", "").strip()),
            context.get("scope", "all"),
        )
    if "describe" in task_lower or "document" in task_lower or "info" in task_lower:
        return describe(
            context.get("table", "target_table"),
            context.get("include_columns", True),
        )
    if "impact" in task_lower or "change" in task_lower:
        return impact_analysis(
            context.get("table", "target_table"),
            context.get("changes", []),
        )
    if "tag" in task_lower:
        return tag(
            context.get("entity_type", "table"),
            context.get("entity_name", context.get("table", "target_table")),
            context.get("tags", []),
            context.get("action", "add"),
        )
    return describe(context.get("table", "target_table"))


_CATALOG: dict[str, dict] = {
    "tables": {},
    "tags": {},
    "usage": {},
}


def _ensure_table(table: str) -> dict:
    """Get or create a table entry in the catalog."""
    if table not in _CATALOG["tables"]:
        _CATALOG["tables"][table] = {
            "name": table,
            "description": "",
            "columns": {},
            "tags": [],
            "created_at": None,
            "updated_at": None,
        }
    return _CATALOG["tables"][table]


def search(query: str, scope: str = "all") -> dict:
    """Search for tables, columns, and tags matching a query.

    scope: "tables" | "columns" | "tags" | "all"
    """
    q = query.lower()
    results: dict[str, list] = {"tables": [], "columns": [], "tags": []}

    for table_name, table_data in _CATALOG["tables"].items():
        # Search tables
        if scope in ("all", "tables"):
            if q in table_name.lower() or q in table_data.get("description", "").lower():
                results["tables"].append({
                    "name": table_name,
                    "description": table_data.get("description", ""),
                    "tags": table_data.get("tags", []),
                    "column_count": len(table_data.get("columns", {})),
                })

        # Search columns
        if scope in ("all", "columns"):
            for col_name, col_data in table_data.get("columns", {}).items():
                if q in col_name.lower() or q in col_data.get("description", "").lower():
                    results["columns"].append({
                        "table": table_name,
                        "column": col_name,
                        "type": col_data.get("type", ""),
                        "description": col_data.get("description", ""),
                    })

        # Search tags
        if scope in ("all", "tags"):
            for tag_val in table_data.get("tags", []):
                if q in tag_val.lower():
                    if tag_val not in [t["name"] for t in results["tags"]]:
                        results["tags"].append({"name": tag_val, "table_count": 0})

    # Count tables per tag
    tag_table_counts: dict[str, int] = {}
    for table_data in _CATALOG["tables"].values():
        for tag_val in table_data.get("tags", []):
            tag_table_counts[tag_val] = tag_table_counts.get(tag_val, 0) + 1
    for t in results["tags"]:
        t["table_count"] = tag_table_counts.get(t["name"], 0)

    result_count = len(results["tables"]) + len(results["columns"]) + len(results["tags"])
    return {
        "query": query,
        "total_results": result_count,
        **results,
    }


def describe(table: str, include_columns: bool = True) -> dict:
    """Get documentation for a table: schema, columns, tags, usage."""
    table_data = _ensure_table(table)

    result = {
        "name": table_data["name"],
        "description": table_data.get("description", ""),
        "tags": table_data.get("tags", []),
        "column_count": len(table_data.get("columns", {})),
    }

    if include_columns:
        columns = []
        for col_name, col_data in table_data.get("columns", {}).items():
            columns.append({
                "name": col_name,
                "type": col_data.get("type", ""),
                "description": col_data.get("description", ""),
                "nullable": col_data.get("nullable", True),
                "tags": col_data.get("tags", []),
            })
        result["columns"] = columns

    # Usage info
    usage = _CATALOG["usage"].get(table, {})
    if usage:
        result["usage"] = {
            "downstream_pipelines": usage.get("downstream", []),
            "upstream_sources": usage.get("upstream", []),
            "query_count": usage.get("query_count", 0),
        }

    return result


def impact_analysis(table: str, changes: list[dict]) -> dict:
    """Analyze impact of schema changes on downstream dependencies.

    changes: list of {"type": "drop"|"rename"|"modify", "column": str, ...}
    """
    _ensure_table(table)  # ensure entry exists
    usage = _CATALOG["usage"].get(table, {})
    downstream = usage.get("downstream", [])

    impacts = []
    for change in changes:
        impact: dict = {
            "change": change,
            "severity": "low",
            "affected_pipelines": [],
            "recommendation": "",
        }

        if change["type"] == "drop":
            impact["severity"] = "high"
            # Find which pipelines use this column
            for d in downstream:
                if change.get("column") in d.get("columns", []):
                    impact["affected_pipelines"].append(d["name"])
            impact["recommendation"] = (
                f"Remove all references to {change['column']} before dropping. "
                f"Affects {len(impact['affected_pipelines'])} pipeline(s)."
            )

        elif change["type"] == "rename":
            impact["severity"] = "medium"
            for d in downstream:
                if change.get("column") in d.get("columns", []):
                    impact["affected_pipelines"].append(d["name"])
            impact["recommendation"] = (
                f"Update all references from {change['column']} to {change.get('new_name', '')}. "
                f"Use ALTER TABLE RENAME to preserve downstream compatibility during transition."
            )

        elif change["type"] == "modify":
            impact["severity"] = "medium"
            for d in downstream:
                if change.get("column") in d.get("columns", []):
                    impact["affected_pipelines"].append(d["name"])
            impact["recommendation"] = (
                f"Verify type compatibility for {change['column']} across "
                f"{len(impact['affected_pipelines'])} downstream pipeline(s)."
            )

        impacts.append(impact)

    high_count = sum(1 for i in impacts if i["severity"] == "high")
    medium_count = sum(1 for i in impacts if i["severity"] == "medium")

    return {
        "table": table,
        "total_impacts": len(impacts),
        "high_severity": high_count,
        "medium_severity": medium_count,
        "impacts": impacts,
    }


def tag(
    entity_type: str,
    entity_name: str,
    tags: list[str],
    action: str = "add",
) -> dict:
    """Add or remove tags from a table or column.

    entity_type: "table" | "column"
    entity_name: "table_name" or "table_name.column_name"
    action: "add" | "remove" | "set"
    """
    if entity_type == "table":
        table_data = _ensure_table(entity_name)
        current_tags = set(table_data.get("tags", []))
    elif entity_type == "column":
        parts = entity_name.split(".")
        if len(parts) != 2:
            return {"status": "error", "message": "Column must be specified as table.column"}
        table_name, col_name = parts
        table_data = _ensure_table(table_name)
        if col_name not in table_data["columns"]:
            table_data["columns"][col_name] = {"name": col_name, "type": "unknown", "tags": []}
        current_tags = set(table_data["columns"][col_name].get("tags", []))
    else:
        return {"status": "error", "message": f"Unknown entity type: {entity_type}"}

    if action == "add":
        current_tags.update(tags)
    elif action == "remove":
        current_tags.difference_update(tags)
    elif action == "set":
        current_tags = set(tags)

    new_tags = sorted(current_tags)

    if entity_type == "table":
        table_data["tags"] = new_tags
    else:
        table_data["columns"][col_name]["tags"] = new_tags

    return {
        "status": "success",
        "entity": entity_name,
        "tags": new_tags,
        "action": action,
    }
