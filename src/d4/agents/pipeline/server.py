import sqlparse
from typing import Optional


def execute(task: str, context: dict) -> dict:
    """Main entry point — called by orchestrator. Routes to the right pipeline tool."""
    task_lower = task.lower()
    if "generate" in task_lower or "create" in task_lower:
        source = context.get("source", context.get("source_table", "source_table"))
        target = context.get("target", context.get("target_table", "target_table"))
        transforms = context.get("transformations")
        return generate_pipeline(source, target, transforms)
    if "debug" in task_lower:
        sql = context.get("sql", "")
        return debug_sql(sql) if sql else {"error": "No SQL provided"}
    if "explain" in task_lower or "analyze" in task_lower:
        sql = context.get("sql", "")
        return explain_plan(sql) if sql else {"error": "No SQL provided"}
    if "spark" in task_lower:
        return run_spark(
            context.get("job_name", task.replace("spark", "").strip()),
            context.get("script", "job.py"),
            context.get("config"),
        )
    tables = [w for w in task_lower.split() if w.isalnum() and len(w) > 2]
    source = tables[-2] if len(tables) >= 2 else "source"
    target = tables[-1] if tables else "target"
    return generate_pipeline(source, target)


def generate_pipeline(
    source_table: str,
    target_table: str,
    transformations: Optional[list[str]] = None,
) -> dict:
    """Generate a SQL pipeline skeleton from source to target."""
    if transformations is None:
        transformations = ["deduplicate", "cast_types"]

    steps = []
    step_num = 1

    # Step 1: Extract
    steps.append(f"-- Step {step_num}: Extract from {source_table}")
    steps.append(f"SELECT * FROM {source_table};")
    step_num += 1

    # Step 2: Transformations
    for t in transformations:
        steps.append(f"-- Step {step_num}: {t}")
        if t == "filter_nulls":
            steps.append("-- WHERE column IS NOT NULL  -- add specific columns")
        elif t == "cast_types":
            steps.append("-- CAST(column AS type)  -- specify columns and types")
        elif t == "deduplicate":
            steps.append("-- ROW_NUMBER() OVER (PARTITION BY id ORDER BY updated_at DESC) AS rn\n-- WHERE rn = 1")
        else:
            steps.append(f"-- TODO: implement {t}")
        step_num += 1

    # Step 3: Load
    steps.append(f"-- Step {step_num}: Load to {target_table}")
    steps.append(f"INSERT INTO {target_table}\nSELECT * FROM stage;")

    return {
        "source_table": source_table,
        "target_table": target_table,
        "transformations": transformations,
        "steps": steps,
        "sql": "\n\n".join(steps),
    }


def debug_sql(sql: str) -> dict:
    """Analyze and format a SQL query."""
    formatted = sqlparse.format(sql, reindent=True, keyword_case='upper')
    parsed = sqlparse.parse(sql)

    clauses = []
    for stmt in parsed:
        for token in stmt.tokens:
            if token.ttype is not None:
                clauses.append({
                    "type": str(token.ttype),
                    "value": token.value[:80] if len(str(token.value)) > 80 else token.value,
                })
            elif hasattr(token, 'tokens'):
                clauses.append({
                    "type": "group",
                    "value": str(type(token).__name__),
                })

    return {
        "is_valid": True if sql.strip() else False,
        "formatted": formatted,
        "analysis": {
            "statement_count": len(parsed),
            "clauses": clauses,
        },
    }


def run_spark(job_name: str, script_path: str, config: dict | None = None) -> dict:
    """Generate a PySpark job configuration and plan.

    This tool doesn't execute Spark directly — it generates the job config,
    argument list, and monitoring commands that the user can run.
    """
    if config is None:
        config = {}

    spark_config = {
        "spark.master": config.get("master", "yarn"),
        "spark.executor.memory": config.get("executor_memory", "4g"),
        "spark.executor.instances": config.get("executor_instances", 4),
        "spark.driver.memory": config.get("driver_memory", "2g"),
        "spark.sql.shuffle.partitions": config.get("shuffle_partitions", 200),
    }

    submit_command = [
        "spark-submit",
        f"--name", job_name,
    ]
    for k, v in spark_config.items():
        submit_command.extend([f"--conf", f"{k}={v}"])
    submit_command.append(script_path)

    return {
        "job_name": job_name,
        "script": script_path,
        "spark_config": spark_config,
        "submit_command": " \\\n  ".join(submit_command),
        "monitoring": f"spark.yarn.ui.port={config.get('ui_port', 8088)}",
        "estimated_resources": {
            "total_memory_gb": spark_config["spark.executor.instances"] * int(spark_config["spark.executor.memory"][:-1]),
            "total_cores": spark_config["spark.executor.instances"] * 4,
        },
    }


def explain_plan(sql: str) -> dict:
    """Break down a SQL query into logical operations."""
    parsed = sqlparse.parse(sql)
    if not parsed or len(sql.strip()) == 0:
        return {"query_type": "unknown", "operations": ["Unable to parse query"]}

    stmt = parsed[0]
    query_type = "SELECT"
    table = "unknown"
    columns = ["*"]
    operations = []

    for token in stmt.tokens:
        if token.ttype is sqlparse.tokens.DML:
            query_type = token.value.upper()
            break

    from_seen = False
    for token in stmt.tokens:
        if token.ttype is sqlparse.tokens.Keyword and token.value.upper() == "FROM":
            from_seen = True
            continue
        if from_seen and isinstance(token, sqlparse.sql.Identifier):
            table = str(token.get_real_name()) if hasattr(token, 'get_real_name') else str(token)
            break
        if from_seen and isinstance(token, sqlparse.sql.Where):
            break

    # Detect operations
    for token in stmt.tokens:
        val = token.value.upper() if hasattr(token, 'value') else ''
        if val == "WHERE":
            operations.append("Filter (WHERE)")
        elif val == "ORDER BY":
            operations.append("Sort (ORDER BY)")
        elif val == "GROUP BY":
            operations.append("Aggregate (GROUP BY)")
        elif val == "LIMIT":
            operations.append("Limit (LIMIT)")
        elif val in ("DISTINCT",):
            operations.append(f"Unique ({val})")

    if not operations:
        operations.append(f"Scan table: {table}")

    return {
        "query_type": query_type,
        "table": table,
        "columns": columns,
        "operations": operations,
    }
