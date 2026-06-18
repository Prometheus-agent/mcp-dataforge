"""Schema Agent — drift detection, migration generation, schema linting, lineage."""


def execute(task: str, context: dict) -> dict:
    """Main entry point — called by orchestrator."""
    task_lower = task.lower()
    if "drift" in task_lower:
        return detect_drift(
            context.get("source_columns", []),
            context.get("target_columns", []),
        )
    if "migration" in task_lower or "migrate" in task_lower:
        return generate_migration(
            context.get("source_columns", []),
            context.get("target_columns", []),
            context.get("table", "target_table"),
        )
    if "lint" in task_lower:
        return lint_schema(
            context.get("columns", []),
            context.get("conventions"),
        )
    if "lineage" in task_lower or "trace" in task_lower:
        return lineage(
            context.get("table", ""),
            context.get("columns", []),
            context.get("transformations", []),
        )
    return detect_drift(context.get("source_columns", []), context.get("target_columns", []))


def detect_drift(source_columns: list[dict], target_columns: list[dict]) -> dict:
    """Compare two column schemas and report drift.

    Each column dict: {"name": str, "type": str, "nullable": bool, "description": str?}
    """
    source_map = {c["name"]: c for c in source_columns}
    target_map = {c["name"]: c for c in target_columns}

    added = [c for c in target_columns if c["name"] not in source_map]
    removed = [c for c in source_columns if c["name"] not in target_map]

    modified = []
    for name, src_col in source_map.items():
        tgt_col = target_map.get(name)
        if tgt_col and src_col != tgt_col:
            changes = []
            if src_col.get("type") != tgt_col.get("type"):
                changes.append(f"type: {src_col.get('type')} -> {tgt_col.get('type')}")
            if src_col.get("nullable") != tgt_col.get("nullable"):
                changes.append(f"nullable: {src_col.get('nullable')} -> {tgt_col.get('nullable')}")
            modified.append({"name": name, "changes": changes})

    return {
        "total_source": len(source_columns),
        "total_target": len(target_columns),
        "added": added,
        "removed": removed,
        "modified": modified,
        "has_drift": bool(added or removed or modified),
    }


def generate_migration(source_columns: list[dict], target_columns: list[dict], table: str = "target_table") -> dict:
    """Generate SQL migration from source schema to target schema."""
    source_map = {c["name"]: c for c in source_columns}
    target_map = {c["name"]: c for c in target_columns}

    statements = []

    # New tables
    if not source_columns and target_columns:
        cols = ", ".join(
            f"{c['name']} {c['type']}{'' if c.get('nullable', True) else ' NOT NULL'}"
            for c in target_columns
        )
        statements.append(f"CREATE TABLE {table} ({cols});")
        return {"statements": statements, "type": "create"}

    # Dropped columns
    for c in source_columns:
        if c["name"] not in target_map:
            statements.append(f"ALTER TABLE {table} DROP COLUMN IF EXISTS {c['name']};")

    # Added columns
    for c in target_columns:
        if c["name"] not in source_map:
            nullable = "" if c.get("nullable", True) else " NOT NULL"
            statements.append(f"ALTER TABLE {table} ADD COLUMN {c['name']} {c['type']}{nullable};")

    # Modified columns
    for name, src in source_map.items():
        tgt = target_map.get(name)
        if tgt and src.get("type") != tgt.get("type"):
            statements.append(f"ALTER TABLE {table} ALTER COLUMN {name} TYPE {tgt['type']};")
        if tgt and src.get("nullable") != tgt.get("nullable"):
            if tgt.get("nullable"):
                statements.append(f"ALTER TABLE {table} ALTER COLUMN {name} DROP NOT NULL;")
            else:
                statements.append(f"ALTER TABLE {table} ALTER COLUMN {name} SET NOT NULL;")

    return {
        "statements": statements,
        "type": "migration",
        "table": table,
    }


def lint_schema(columns: list[dict], conventions: dict | None = None) -> dict:
    """Lint a schema against naming conventions and best practices.

    conventions: {"naming_case": "snake_case"|"camelCase", "require_descriptions": bool, "require_not_null": bool}
    """
    if conventions is None:
        conventions = {"naming_case": "snake_case", "require_descriptions": False, "require_not_null": False}

    issues = []

    for col in columns:
        name = col["name"]

        # Naming convention checks
        if conventions.get("naming_case") == "snake_case":
            if any(c.isupper() for c in name):
                issues.append({
                    "column": name,
                    "severity": "warning",
                    "rule": "naming_case",
                    "message": f"Column '{name}' should use snake_case",
                })
            if " " in name:
                issues.append({
                    "column": name,
                    "severity": "error",
                    "rule": "no_spaces",
                    "message": f"Column '{name}' contains spaces",
                })

        elif conventions.get("naming_case") == "camelCase":
            if "_" in name:
                issues.append({
                    "column": name,
                    "severity": "warning",
                    "rule": "naming_case",
                    "message": f"Column '{name}' should use camelCase",
                })

        # Description check
        if conventions.get("require_descriptions") and not col.get("description"):
            issues.append({
                "column": name,
                "severity": "info",
                "rule": "missing_description",
                "message": f"Column '{name}' is missing a description",
            })

        # NOT NULL check
        if conventions.get("require_not_null") and col.get("nullable", True):
            issues.append({
                "column": name,
                "severity": "warning",
                "rule": "nullable_column",
                "message": f"Column '{name}' is nullable but should be NOT NULL",
            })

        # Type-specific checks
        if col.get("type", "").upper() in ("TEXT", "VARCHAR", "STRING"):
            if "name" in name.lower() or "desc" in name.lower():
                if col.get("nullable", True):
                    pass  # OK, names can be nullable
            if "id" in name.lower() and col.get("type", "").upper() not in ("INTEGER", "BIGINT", "UUID"):
                issues.append({
                    "column": name,
                    "severity": "warning",
                    "rule": "id_type",
                    "message": f"Column '{name}' looks like an ID but is {col['type']}",
                })

    return {
        "columns_checked": len(columns),
        "issues": issues,
        "issue_count": len(issues),
        "has_issues": len(issues) > 0,
    }


def lineage(table: str, columns: list[str], transformations: list[dict]) -> dict:
    """Trace column-level lineage through transformations.

    transformations: list of {"source_table": str, "source_column": str, "target_column": str, "transform": str}
    """
    # Build upstream and downstream maps
    upstream = {}  # column -> list of sources
    downstream = {}  # column -> list of targets

    for t in transformations:
        src_key = f"{t['source_table']}.{t['source_column']}"
        tgt_key = f"{table}.{t['target_column']}"

        if tgt_key not in upstream:
            upstream[tgt_key] = []
        upstream[tgt_key].append({
            "source": src_key,
            "transform": t.get("transform", "direct"),
        })

        if src_key not in downstream:
            downstream[src_key] = []
        downstream[src_key].append({
            "target": tgt_key,
            "transform": t.get("transform", "direct"),
        })

    column_lineage = {}
    for col in columns:
        col_key = f"{table}.{col}"
        column_lineage[col] = {
            "upstream": upstream.get(col_key, []),
            "downstream": downstream.get(col_key, []),
        }

    return {
        "table": table,
        "columns": column_lineage,
    }
