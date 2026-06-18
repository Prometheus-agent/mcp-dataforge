import pytest
from d4.agents.orchestration.server import (
    create_dag, manage_retry, resolve_deps, backfill,
)


@pytest.fixture(autouse=True)
def reset_store():
    import d4.agents.orchestration.server as srv
    srv._STORE["dags"].clear()
    srv._STORE["runs"].clear()


class TestCreateDag:
    def test_create_simple_dag(self):
        result = create_dag("simple_pipeline", description="Simple ETL", schedule="@daily")
        assert result["status"] == "success"
        assert result["dag_id"] == "simple_pipeline"
        assert result["task_count"] == 0

    def test_create_dag_with_tasks(self):
        tasks = [
            {"id": "extract", "command": "python extract.py", "depends_on": []},
            {"id": "transform", "command": "python transform.py", "depends_on": ["extract"]},
            {"id": "load", "command": "python load.py", "depends_on": ["transform"]},
        ]
        result = create_dag("etl_pipeline", tasks=tasks)
        assert result["status"] == "success"
        assert result["task_count"] == 3
        assert result["topological_order"] == ["extract", "transform", "load"]

    def test_duplicate_dag(self):
        create_dag("dup", schedule="@daily")
        result = create_dag("dup", schedule="@daily")
        assert result["status"] == "error"

    def test_missing_dependency(self):
        tasks = [
            {"id": "task_a", "depends_on": ["nonexistent"]},
        ]
        result = create_dag("bad", tasks=tasks)
        assert result["status"] == "error"

    def test_circular_dependency(self):
        tasks = [
            {"id": "a", "depends_on": ["c"]},
            {"id": "b", "depends_on": ["a"]},
            {"id": "c", "depends_on": ["b"]},
        ]
        result = create_dag("circular", tasks=tasks)
        assert result["status"] == "error"

    def test_parallel_tasks(self):
        tasks = [
            {"id": "start", "depends_on": []},
            {"id": "branch_a", "depends_on": ["start"]},
            {"id": "branch_b", "depends_on": ["start"]},
            {"id": "join", "depends_on": ["branch_a", "branch_b"]},
        ]
        result = create_dag("parallel_dag", tasks=tasks)
        assert result["status"] == "success"
        assert result["task_count"] == 4
        # start -> [branch_a, branch_b] -> join


class TestManageRetry:
    def test_retry_task(self):
        create_dag("retry_test", tasks=[{"id": "task1", "depends_on": []}])
        result = manage_retry("retry_test", "task1", action="retry")
        assert result["status"] == "success"
        assert result["action"] == "retry_triggered"

    def test_configure_retries(self):
        create_dag("cfg_test", tasks=[{"id": "task1", "depends_on": []}])
        result = manage_retry("cfg_test", "task1", action="configure", max_retries=5)
        assert result["status"] == "success"
        assert result["max_retries"] == 5

    def test_skip_task(self):
        create_dag("skip_test", tasks=[{"id": "task1", "depends_on": []}])
        result = manage_retry("skip_test", "task1", action="skip")
        assert result["status"] == "success"
        assert result["action"] == "skipped"

    def test_nonexistent_dag(self):
        result = manage_retry("no_dag", "task1")
        assert result["status"] == "error"

    def test_nonexistent_task(self):
        create_dag("exists", tasks=[{"id": "real_task", "depends_on": []}])
        result = manage_retry("exists", "fake_task")
        assert result["status"] == "error"


class TestResolveDeps:
    def test_empty_dag(self):
        create_dag("empty")
        result = resolve_deps("empty")
        assert result["task_count"] == 0

    def test_linear_dag(self):
        tasks = [
            {"id": "a", "depends_on": []},
            {"id": "b", "depends_on": ["a"]},
            {"id": "c", "depends_on": ["b"]},
        ]
        create_dag("linear", tasks=tasks)
        result = resolve_deps("linear")
        assert result["task_count"] == 3
        assert result["levels"] == [["a"], ["b"], ["c"]]
        assert "a" in result["critical_path"]

    def test_parallel_dag_levels(self):
        tasks = [
            {"id": "start", "depends_on": []},
            {"id": "a", "depends_on": ["start"]},
            {"id": "b", "depends_on": ["start"]},
        ]
        create_dag("parallel", tasks=tasks)
        result = resolve_deps("parallel")
        assert result["can_parallelize"] is True
        assert len(result["levels"][1]) == 2  # a and b at same level

    def test_nonexistent_dag(self):
        result = resolve_deps("ghost")
        assert result["status"] == "error"


class TestBackfill:
    def test_dry_run(self):
        tasks = [{"id": "t1", "depends_on": []}]
        create_dag("daily_job", tasks=tasks, schedule="@daily")
        result = backfill("daily_job", "2026-01-01", "2026-01-03", dry_run=True)
        assert result["status"] == "planned"
        assert result["total_intervals"] == 3

    def test_backfill_invalid_dates(self):
        result = backfill("nonexistent", "2026-01-01", "2026-01-03")
        assert result["status"] == "error"

    def test_backfill_end_before_start(self):
        result = backfill("nonexistent", "2026-01-05", "2026-01-01")
        assert result["status"] == "error"

    def test_execute_backfill(self):
        tasks = [{"id": "t1", "depends_on": []}, {"id": "t2", "depends_on": ["t1"]}]
        create_dag("backfill_test", tasks=tasks, schedule="@daily")
        result = backfill("backfill_test", "2026-01-01", "2026-01-02", dry_run=False)
        assert result["status"] == "executed"
        assert result["total_runs"] == 4  # 2 days * 2 tasks
