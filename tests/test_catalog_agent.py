import pytest
from d4.agents.catalog.server import search, describe, impact_analysis, tag, sync_from_db


# Reset catalog state before each test
@pytest.fixture(autouse=True)
def reset_catalog():
    import d4.agents.catalog.server as srv
    srv._CATALOG["tables"].clear()
    srv._CATALOG["tags"].clear()
    srv._CATALOG["usage"].clear()

    # Seed some test data
    srv._ensure_table("orders")
    srv._ensure_table("customers")
    srv._CATALOG["tables"]["orders"]["description"] = "Customer order records"
    srv._CATALOG["tables"]["orders"]["columns"] = {
        "id": {"name": "id", "type": "INTEGER", "description": "Order ID", "nullable": False},
        "customer_id": {"name": "customer_id", "type": "INTEGER", "description": "Customer FK", "nullable": False},
        "total": {"name": "total", "type": "FLOAT", "description": "Order total", "nullable": True},
        "status": {"name": "status", "type": "VARCHAR", "description": "", "nullable": True},
    }
    srv._CATALOG["tables"]["orders"]["tags"] = ["pii", "production"]
    srv._CATALOG["tables"]["customers"]["description"] = "Customer master data"
    srv._CATALOG["tables"]["customers"]["tags"] = ["pii"]

    srv._CATALOG["usage"]["orders"] = {
        "downstream": [{"name": "daily_revenue", "columns": ["total", "status"]}],
        "upstream": [{"name": "payment_events"}],
        "query_count": 150,
    }


class TestSearch:
    def test_search_by_table_name(self):
        result = search("orders")
        assert result["total_results"] >= 1
        assert any(t["name"] == "orders" for t in result["tables"])

    def test_search_by_description(self):
        result = search("customer")
        assert len(result["tables"]) >= 1

    def test_search_by_column(self):
        result = search("total", scope="columns")
        assert len(result["columns"]) >= 1
        assert any(c["column"] == "total" for c in result["columns"])

    def test_search_by_tag(self):
        result = search("pii", scope="tags")
        assert len(result["tags"]) >= 1
        assert any(t["name"] == "pii" for t in result["tags"])

    def test_search_no_results(self):
        result = search("nonexistent_xyz")
        assert result["total_results"] == 0


class TestDescribe:
    def test_describe_table_basic(self):
        info = describe("orders")
        assert info["name"] == "orders"
        assert info["description"] == "Customer order records"
        assert "pii" in info["tags"]

    def test_describe_with_columns(self):
        info = describe("orders", include_columns=True)
        assert info["column_count"] == 4
        assert len(info["columns"]) == 4

    def test_describe_without_columns(self):
        info = describe("orders", include_columns=False)
        assert "columns" not in info

    def test_describe_new_table_creates_entry(self):
        info = describe("new_table")
        assert info["name"] == "new_table"
        assert info["description"] == ""

    def test_describe_includes_usage(self):
        info = describe("orders")
        assert "usage" in info
        assert info["usage"]["query_count"] == 150


class TestImpactAnalysis:
    def test_drop_column_high_severity(self):
        result = impact_analysis("orders", [{"type": "drop", "column": "total"}])
        assert result["high_severity"] == 1
        assert "daily_revenue" in result["impacts"][0]["affected_pipelines"]

    def test_rename_medium_severity(self):
        result = impact_analysis(
            "orders", [{"type": "rename", "column": "status", "new_name": "order_status"}]
        )
        assert result["medium_severity"] == 1

    def test_multiple_changes(self):
        result = impact_analysis("orders", [
            {"type": "drop", "column": "id"},
            {"type": "rename", "column": "total", "new_name": "amount"},
        ])
        assert result["total_impacts"] == 2


class TestTag:
    def test_add_tag_to_table(self):
        result = tag("table", "orders", ["critical"])
        assert result["status"] == "success"
        assert "critical" in result["tags"]
        # Verify persisted
        info = describe("orders")
        assert "critical" in info["tags"]

    def test_remove_tag(self):
        tag("table", "orders", ["pii"])
        result = tag("table", "orders", ["pii"], action="remove")
        assert "pii" not in result["tags"]

    def test_set_tags_replaces(self):
        result = tag("table", "orders", ["new_tag"], action="set")
        assert result["tags"] == ["new_tag"]

    def test_tag_column(self):
        result = tag("column", "orders.id", ["primary_key"])
        assert result["status"] == "success"
        assert "primary_key" in result["tags"]

    def test_invalid_entity_type(self):
        result = tag("invalid", "x", ["y"])
        assert result["status"] == "error"


class TestSyncFromDb:
    def test_sync_from_duckdb(self):
        import duckdb
        conn = duckdb.connect(":memory:")
        conn.execute("CREATE TABLE test_sync (id INTEGER, name VARCHAR)")
        conn.execute("INSERT INTO test_sync VALUES (1, 'hello')")

        result = sync_from_db(conn, include_columns=True)
        assert result["tables_added"] >= 1
        assert result["columns_added"] >= 2

        info = describe("test_sync", include_columns=True)
        assert info["column_count"] >= 2

        # Clean up the catalog state for other tests
        import d4.agents.catalog.server as cat
        cat._CATALOG["tables"].clear()

    def test_sync_no_columns(self):
        import duckdb
        conn = duckdb.connect(":memory:")
        conn.execute("CREATE TABLE empty_t (x INTEGER)")

        result = sync_from_db(conn, include_columns=False)
        assert result["tables_added"] >= 1
        assert result["columns_added"] == 0

        import d4.agents.catalog.server as cat
        cat._CATALOG["tables"].clear()
