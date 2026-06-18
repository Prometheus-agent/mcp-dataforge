from d4.agents.pipeline.server import (
    generate_pipeline,
    debug_sql,
    explain_plan,
    run_spark,
)


class TestGeneratePipeline:
    def test_generates_simple_etl(self):
        result = generate_pipeline(
            source_table="orders.raw",
            target_table="orders.clean",
            transformations=["filter_nulls", "cast_types"],
        )
        assert "source_table" in result
        assert result["source_table"] == "orders.raw"
        assert result["target_table"] == "orders.clean"
        assert len(result["steps"]) > 0
        assert result["steps"][0] == "-- Step 1: Extract from orders.raw"

    def test_defaults(self):
        result = generate_pipeline(
            source_table="src",
            target_table="tgt",
        )
        assert len(result["steps"]) >= 2
        assert "INSERT INTO tgt" in result["steps"][-1]


class TestDebugSql:
    def test_formats_sql(self):
        sql = "SELECT a,b FROM t WHERE a>1 ORDER BY b"
        result = debug_sql(sql)
        assert result["is_valid"] is True
        assert "analysis" in result
        assert len(result["analysis"]["clauses"]) > 0

    def test_empty_sql(self):
        sql = "SELECT FROM"
        result = debug_sql(sql)
        assert result["is_valid"] is True  # sqlparse is lenient
        assert len(result["formatted"]) > 0


class TestExplainPlan:
    def test_simple_select(self):
        sql = "SELECT id, name, amount FROM orders WHERE amount > 100 ORDER BY created_at DESC"
        result = explain_plan(sql)
        assert result["query_type"] == "SELECT"
        assert "orders" in result["table"]
        assert len(result["operations"]) > 0


class TestRunSpark:
    def test_generates_spark_job(self):
        result = run_spark("etl_job", "transform.py")
        assert result["job_name"] == "etl_job"
        assert "spark-submit" in result["submit_command"]
        assert "spark.executor.memory" in result["spark_config"]

    def test_custom_config(self):
        result = run_spark("test", "test.py", {"executor_memory": "8g", "executor_instances": 8})
        assert result["spark_config"]["spark.executor.memory"] == "8g"
        assert result["estimated_resources"]["total_memory_gb"] == 64
