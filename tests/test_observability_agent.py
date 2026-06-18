import pytest
from d4.agents.observability.server import (
    get_pipeline_health, alert_summary, cost_analysis, suggest_optimizations,
    record_run, record_alert,
)


@pytest.fixture(autouse=True)
def seed_data():
    import d4.agents.observability.server as srv
    srv._STORE["pipelines"].clear()
    srv._STORE["alerts"].clear()
    srv._STORE["runs"].clear()

    # Seed pipeline runs
    for i in range(10):
        status = "success" if i < 8 else "failed"
        record_run("daily_revenue", status, duration_min=15.0 + i, rows_processed=1_000_000)

    for i in range(5):
        record_run("customer_etl", "success", duration_min=45.0, rows_processed=15_000_000)

    # Seed alerts
    record_alert("daily_revenue", "critical", "Pipeline failed: null pointer in revenue calculation")
    record_alert("daily_revenue", "warning", "Data freshness SLA at risk: delay of 30min")
    record_alert("customer_etl", "warning", "Row count deviation: expected 15M, got 14.2M")
    record_alert("customer_etl", "info", "New column detected: loyalty_tier")


class TestGetPipelineHealth:
    def test_healthy_pipeline(self):
        health = get_pipeline_health("daily_revenue")
        assert health["pipeline"] == "daily_revenue"
        assert health["health"] in ("healthy", "degraded")
        assert health["success_rate"] > 0
        assert len(health["recent_runs_summary"]) > 0

    def test_unknown_pipeline(self):
        health = get_pipeline_health("nonexistent")
        assert health["pipeline"] == "nonexistent"
        assert health["health"] == "healthy"
        assert health["status"] == "unknown"

    def test_includes_alerts(self):
        health = get_pipeline_health("daily_revenue")
        assert "active_alerts" in health
        assert "recent_alerts" in health


class TestAlertSummary:
    def test_all_alerts(self):
        summary = alert_summary("all")
        assert summary["total_alerts"] == 4

    def test_filter_by_severity(self):
        critical = alert_summary("critical")
        assert critical["total_alerts"] == 1
        warning = alert_summary("warning")
        assert warning["total_alerts"] == 2

    def test_pipelines_affected(self):
        summary = alert_summary("all")
        assert summary["pipelines_affected"] >= 2


class TestCostAnalysis:
    def test_all_providers(self):
        result = cost_analysis()
        assert result["monthly_total"] > 0
        assert len(result["providers"]) >= 3
        assert result["top_provider"] is not None

    def test_single_provider(self):
        result = cost_analysis(provider="snowflake")
        assert len(result["providers"]) == 1
        assert result["providers"][0]["name"] == "snowflake"

    def test_has_recommendations(self):
        result = cost_analysis()
        assert "recommendations" in result
        assert result["total_potential_savings"] > 0


class TestSuggestOptimizations:
    def test_customer_etl_long_runtime(self):
        result = suggest_optimizations("customer_etl")
        assert result["pipeline"] == "customer_etl"
        assert len(result["suggestions"]) > 0
        # Should flag long runtime
        categories = [s["category"] for s in result["suggestions"]]
        assert "performance" in categories

    def test_daily_revenue_has_failures(self):
        result = suggest_optimizations("daily_revenue")
        categories = [s["category"] for s in result["suggestions"]]
        assert "reliability" in categories

    def test_unknown_pipeline_returns_info(self):
        result = suggest_optimizations("brand_new")
        assert len(result["suggestions"]) >= 1
        assert result["suggestions"][0]["category"] == "info"
