import pytest
from d4.agents.schema.server import detect_drift, generate_migration, lint_schema, lineage


class TestDetectDrift:
    def test_no_drift(self):
        source = [{"name": "id", "type": "INTEGER"}, {"name": "name", "type": "VARCHAR"}]
        target = [{"name": "id", "type": "INTEGER"}, {"name": "name", "type": "VARCHAR"}]
        result = detect_drift(source, target)
        assert result["has_drift"] is False
        assert len(result["added"]) == 0
        assert len(result["removed"]) == 0
        assert len(result["modified"]) == 0

    def test_added_columns(self):
        source = [{"name": "id", "type": "INTEGER"}]
        target = [{"name": "id", "type": "INTEGER"}, {"name": "email", "type": "VARCHAR"}]
        result = detect_drift(source, target)
        assert result["has_drift"] is True
        assert len(result["added"]) == 1
        assert result["added"][0]["name"] == "email"

    def test_removed_columns(self):
        source = [{"name": "id", "type": "INTEGER"}, {"name": "old_col", "type": "VARCHAR"}]
        target = [{"name": "id", "type": "INTEGER"}]
        result = detect_drift(source, target)
        assert result["has_drift"] is True
        assert len(result["removed"]) == 1
        assert result["removed"][0]["name"] == "old_col"

    def test_modified_type(self):
        source = [{"name": "price", "type": "INTEGER"}]
        target = [{"name": "price", "type": "FLOAT"}]
        result = detect_drift(source, target)
        assert result["has_drift"] is True
        assert result["modified"][0]["changes"][0] == "type: INTEGER -> FLOAT"


class TestGenerateMigration:
    def test_create_table(self):
        result = generate_migration([], [{"name": "id", "type": "INTEGER", "nullable": False}], "users")
        assert result["type"] == "create"
        assert len(result["statements"]) == 1

    def test_add_column(self):
        source = [{"name": "id", "type": "INTEGER"}]
        target = [{"name": "id", "type": "INTEGER"}, {"name": "email", "type": "VARCHAR"}]
        result = generate_migration(source, target, "users")
        assert "ADD COLUMN" in result["statements"][0]

    def test_drop_column(self):
        source = [{"name": "id", "type": "INTEGER"}, {"name": "old", "type": "VARCHAR"}]
        target = [{"name": "id", "type": "INTEGER"}]
        result = generate_migration(source, target, "users")
        assert "DROP COLUMN" in result["statements"][0]

    def test_type_change(self):
        source = [{"name": "price", "type": "INTEGER"}]
        target = [{"name": "price", "type": "FLOAT"}]
        result = generate_migration(source, target, "products")
        assert "ALTER COLUMN" in result["statements"][0]


class TestLintSchema:
    def test_snake_case_pass(self):
        cols = [{"name": "user_id", "type": "INTEGER"}]
        result = lint_schema(cols)
        assert result["has_issues"] is False

    def test_camelcase_warning(self):
        cols = [{"name": "userId", "type": "INTEGER"}]
        result = lint_schema(cols, {"naming_case": "snake_case"})
        assert result["has_issues"] is True
        assert result["issues"][0]["rule"] == "naming_case"

    def test_missing_description(self):
        cols = [{"name": "id", "type": "INTEGER", "description": ""}]
        result = lint_schema(cols, {"require_descriptions": True})
        assert result["has_issues"] is True

    def test_no_issues_with_all_requirements_met(self):
        cols = [{"name": "user_id", "type": "INTEGER", "nullable": False, "description": "Primary key"}]
        result = lint_schema(cols, {"require_descriptions": True, "require_not_null": True, "naming_case": "snake_case"})
        assert result["has_issues"] is False


class TestLineage:
    def test_trace_upstream(self):
        table = "orders"
        columns = ["total_price"]
        transformations = [
            {"source_table": "order_items", "source_column": "price", "target_column": "total_price", "transform": "SUM"},
        ]
        result = lineage(table, columns, transformations)
        assert "total_price" in result["columns"]
        assert len(result["columns"]["total_price"]["upstream"]) == 1
        assert result["columns"]["total_price"]["upstream"][0]["source"] == "order_items.price"

    def test_trace_downstream(self):
        table = "order_items"
        columns = ["price"]
        transformations = [
            {"source_table": "order_items", "source_column": "price", "target_column": "total_price", "transform": "SUM"},
        ]
        result = lineage(table, columns, transformations)
        assert len(result["columns"]["price"]["downstream"]) == 1
