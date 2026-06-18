import pytest
import duckdb
from d4.agents.dq.server import profile_data, detect_anomalies, validate_rules


@pytest.fixture
def db():
    """Create an in-memory DuckDB with test data."""
    conn = duckdb.connect(":memory:")
    conn.execute("""
        CREATE TABLE test_users AS SELECT * FROM (VALUES
            (1, 'alice@email.com', 30, 'active'),
            (2, 'bob@email.com', 25, 'active'),
            (3, NULL, 35, 'active'),
            (4, 'dave@email.com', -5, 'inactive'),
            (5, 'eve@email.com', 150, 'unknown'),
            (6, 'frank@email.com', NULL, 'active'),
            (7, NULL, 28, 'active'),
            (8, 'grace@email.com', 42, 'inactive'),
        ) AS t(id, email, age, status)
    """)
    conn.execute("""
        CREATE TABLE test_metrics AS SELECT * FROM (VALUES
            ('2024-01-01', 100.0),
            ('2024-01-02', 102.0),
            ('2024-01-03', 98.0),
            ('2024-01-04', 101.0),
            ('2024-01-05', 500.0),  -- anomaly
            ('2024-01-06', 99.0),
            ('2024-01-07', 103.0),
            ('2024-01-08', 97.0),
        ) AS t(dt, val)
    """)
    yield conn
    conn.close()


class TestProfileData:
    def test_profiles_table(self, db):
        result = profile_data(db, "test_users")
        assert result["table"] == "test_users"
        assert result["row_count"] == 8
        assert "columns" in result
        columns = {c["name"]: c for c in result["columns"]}

        # Check email column has nulls
        assert columns["email"]["null_count"] == 2
        assert columns["email"]["null_rate"] == 0.25

        # Check age column stats
        assert columns["age"]["min"] == -5
        assert columns["age"]["max"] == 150
        assert columns["age"]["null_count"] == 1

        # Check id column is unique
        assert columns["id"]["distinct_count"] == 8

    def test_with_sample(self, db):
        result = profile_data(db, "test_users", sample_size=5)
        assert result["row_count"] <= 5

    def test_specific_columns(self, db):
        result = profile_data(db, "test_users", columns=["email", "age"])
        assert len(result["columns"]) == 2
        assert {c["name"] for c in result["columns"]} == {"email", "age"}


class TestDetectAnomalies:
    def test_detects_outliers(self, db):
        result = detect_anomalies(
            db,
            "test_metrics",
            time_column="dt",
            metric_column="val",
            threshold=2.0,
        )
        assert result["total_points"] == 8
        assert len(result["anomalies"]) >= 1
        # The 500 value should be flagged
        anomaly_vals = [a["value"] for a in result["anomalies"]]
        assert 500.0 in anomaly_vals

    def test_no_anomalies_with_high_threshold(self, db):
        result = detect_anomalies(
            db,
            "test_metrics",
            time_column="dt",
            metric_column="val",
            threshold=10.0,
        )
        assert len(result["anomalies"]) == 0


class TestValidateRules:
    def test_not_null_rule(self, db):
        result = validate_rules(db, "test_users", [
            {"type": "not_null", "column": "email"},
        ])
        assert len(result["results"]) == 1
        rule_result = result["results"][0]
        assert rule_result["rule"]["type"] == "not_null"
        assert rule_result["passed"] is False
        assert rule_result["failures"] == 2

    def test_unique_rule(self, db):
        result = validate_rules(db, "test_users", [
            {"type": "unique", "column": "id"},
        ])
        assert result["results"][0]["passed"] is True

    def test_multiple_rules(self, db):
        result = validate_rules(db, "test_users", [
            {"type": "not_null", "column": "email"},
            {"type": "min", "column": "age", "value": 0},
            {"type": "max", "column": "age", "value": 120},
        ])
        assert len(result["results"]) == 3
        assert result["pass_rate"] < 1.0  # not all pass

    def test_accepted_values(self, db):
        result = validate_rules(db, "test_users", [
            {"type": "accepted_values", "column": "status", "values": ["active", "inactive"]},
        ])
        # "unknown" should fail
        assert result["results"][0]["passed"] is False
