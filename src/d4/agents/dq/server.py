"""Data Quality Agent — profile, detect anomalies, validate rules."""
from typing import Optional


def profile_data(
    conn,
    table: str,
    columns: Optional[list[str]] = None,
    sample_size: Optional[int] = None,
) -> dict:
    """Profile a table: row count, column stats, null rates, distributions."""
    # Determine table name (handle quoted names)
    quoted_table = f'"{table}"' if "." not in table else table

    # Total row count
    row_count = conn.execute(f"SELECT COUNT(*) FROM {quoted_table}").fetchone()[0]

    # Get column info
    if columns:
        col_list = columns
    else:
        col_info = conn.execute(f"DESCRIBE {quoted_table}").fetchall()
        col_list = [r[0] for r in col_info]

    # If sampling, get a sample first
    if sample_size and sample_size < row_count:
        data_table = f"(SELECT * FROM {quoted_table} USING SAMPLE {sample_size} ROWS)"
        actual_count = sample_size
    else:
        data_table = quoted_table
        actual_count = row_count

    column_stats = []
    for col in col_list:
        quoted_col = f'"{col}"'
        stats = {"name": col}

        # Null stats
        null_count = conn.execute(
            f"SELECT COUNT(*) FROM {data_table} WHERE {quoted_col} IS NULL"
        ).fetchone()[0]
        stats["null_count"] = null_count
        stats["null_rate"] = round(null_count / actual_count, 4) if actual_count > 0 else 0

        # Distinct count
        distinct = conn.execute(
            f"SELECT COUNT(DISTINCT {quoted_col}) FROM {data_table}"
        ).fetchone()[0]
        stats["distinct_count"] = distinct

        # Try numeric stats
        try:
            numeric = conn.execute(f"""
                SELECT
                    MIN({quoted_col}::DOUBLE),
                    MAX({quoted_col}::DOUBLE),
                    AVG({quoted_col}::DOUBLE)
                FROM {data_table}
                WHERE {quoted_col} IS NOT NULL
                  AND TRY_CAST({quoted_col} AS DOUBLE) IS NOT NULL
            """).fetchone()
            if numeric[0] is not None:
                stats["min"] = numeric[0]
                stats["max"] = numeric[1]
                stats["mean"] = round(numeric[2], 2)
                stats["type"] = "numeric"
        except Exception:
            pass

        # Top values (categorical)
        if "type" not in stats or stats.get("distinct_count", 0) <= 20:
            try:
                top = conn.execute(f"""
                    SELECT {quoted_col}, COUNT(*) as cnt
                    FROM {data_table}
                    WHERE {quoted_col} IS NOT NULL
                    GROUP BY {quoted_col}
                    ORDER BY cnt DESC LIMIT 5
                """).fetchall()
                if top:
                    stats["top_values"] = [
                        {"value": str(r[0]), "count": r[1]} for r in top
                    ]
            except Exception:
                pass

        column_stats.append(stats)

    return {
        "table": table,
        "row_count": actual_count,
        "columns": column_stats,
    }


def detect_anomalies(
    conn,
    table: str,
    time_column: str,
    metric_column: str,
    method: str = "zscore",
    threshold: float = 3.0,
) -> dict:
    """Detect anomalies in time-series data using z-score method."""
    quoted_t = f'"{table}"' if "." not in table else table
    qt = f'"{time_column}"'
    qm = f'"{metric_column}"'

    # Compute stats
    stats = conn.execute(f"""
        SELECT
            AVG({qm}) as mean,
            STDDEV_SAMP({qm}) as stddev
        FROM {quoted_t}
        WHERE {qm} IS NOT NULL
    """).fetchone()

    if stats[0] is None or stats[1] is None or stats[1] == 0:
        return {"total_points": 0, "anomalies": [], "method": method, "threshold": threshold}

    mean, stddev = stats[0], stats[1]

    # Compute z-scores and flag anomalies
    rows = conn.execute(f"""
        SELECT
            {qt},
            {qm},
            ({qm} - {mean}) / NULLIF({stddev}, 0) as z_score
        FROM {quoted_t}
        WHERE {qm} IS NOT NULL
        ORDER BY {qt}
    """).fetchall()

    anomalies = []
    for row in rows:
        z = abs(row[2])
        if z > threshold:
            anomalies.append({
                "timestamp": str(row[0]),
                "value": row[1],
                "z_score": round(row[2], 3),
                "severity": "high" if z > threshold * 1.5 else "medium",
            })

    return {
        "total_points": len(rows),
        "anomalies": anomalies,
        "method": method,
        "threshold": threshold,
    }


def validate_rules(conn, table: str, rules: list[dict]) -> dict:
    """Run quality rules against a table and return results."""
    quoted_t = f'"{table}"' if "." not in table else table

    results = []
    total_rules = len(rules)
    passed_rules = 0

    for rule in rules:
        rule_type = rule["type"]
        column = rule.get("column", "")
        qc = f'"{column}"' if column else ""

        result = {"rule": rule, "passed": False, "failures": 0, "failed_rows": []}

        try:
            if rule_type == "not_null":
                failed = conn.execute(
                    f"SELECT {qc} FROM {quoted_t} WHERE {qc} IS NULL"
                ).fetchall()
                result["failures"] = len(failed)
                result["passed"] = result["failures"] == 0
                result["failed_rows"] = [str(r[0]) if r[0] is not None else "NULL" for r in failed[:5]]

            elif rule_type == "unique":
                dupes = conn.execute(f"""
                    SELECT {qc}, COUNT(*) as cnt
                    FROM {quoted_t}
                    WHERE {qc} IS NOT NULL
                    GROUP BY {qc}
                    HAVING COUNT(*) > 1
                """).fetchall()
                total_dupes = sum(r[1] - 1 for r in dupes)
                result["failures"] = total_dupes
                result["passed"] = result["failures"] == 0
                result["failed_rows"] = [str(r[0]) for r in dupes[:5]]

            elif rule_type in ("min", "max"):
                val = rule["value"]
                op = "<" if rule_type == "min" else ">"
                failed = conn.execute(
                    f"SELECT {qc} FROM {quoted_t} WHERE {qc} IS NOT NULL AND {qc} {op} {val}"
                ).fetchall()
                result["failures"] = len(failed)
                result["passed"] = result["failures"] == 0
                result["failed_rows"] = [str(r[0]) for r in failed[:5]]

            elif rule_type == "accepted_values":
                values = rule.get("values", [])
                placeholders = ",".join(f"'{v}'" for v in values)
                failed = conn.execute(
                    f"SELECT {qc} FROM {quoted_t} WHERE {qc} IS NOT NULL AND {qc} NOT IN ({placeholders})"
                ).fetchall()
                result["failures"] = len(failed)
                result["passed"] = result["failures"] == 0
                result["failed_rows"] = [str(r[0]) for r in failed[:5]]

            elif rule_type == "custom_sql":
                sql = rule.get("sql", "")
                failed = conn.execute(sql.replace("{{table}}", quoted_t)).fetchall()
                result["failures"] = len(failed)
                result["passed"] = result["failures"] == 0

            if result["passed"]:
                passed_rules += 1

        except Exception as e:
            result["error"] = str(e)

        results.append(result)

    return {
        "table": table,
        "total_rules": total_rules,
        "passed": passed_rules,
        "failed": total_rules - passed_rules,
        "pass_rate": round(passed_rules / total_rules, 2) if total_rules > 0 else 1.0,
        "results": results,
    }
