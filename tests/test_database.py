"""Tests for database module."""

from __future__ import annotations

import pytest

from analytics_mcp.database import get_schema_info, init_database, query_db


class TestInitDatabase:
    def test_creates_database(self, tmp_path) -> None:
        db_path = tmp_path / "test.db"
        init_database(db_path, force_reseed=True)
        assert db_path.exists()

    def test_force_reseed_resets_data(self, tmp_path) -> None:
        db_path = tmp_path / "test.db"
        init_database(db_path, force_reseed=True)
        rows1 = query_db("SELECT COUNT(*) as c FROM customers")
        init_database(str(db_path), force_reseed=True)
        rows2 = query_db("SELECT COUNT(*) as c FROM customers")
        assert rows1[0]["c"] == rows2[0]["c"]


class TestQueryDb:
    def test_select_customers(self) -> None:
        rows = query_db("SELECT * FROM customers LIMIT 5")
        assert len(rows) == 5
        assert "id" in rows[0]
        assert "name" in rows[0]
        assert "email" in rows[0]

    def test_select_with_params(self) -> None:
        rows = query_db("SELECT * FROM customers WHERE tier = ? LIMIT 3", ("enterprise",))
        assert all(r["tier"] == "enterprise" for r in rows)

    def test_rejects_non_select(self) -> None:
        with pytest.raises(ValueError, match="Only SELECT"):
            query_db("DELETE FROM customers")

    def test_rejects_drop(self) -> None:
        with pytest.raises(ValueError, match="Only SELECT"):
            query_db("DROP TABLE customers")


class TestGetSchemaInfo:
    def test_returns_all_tables(self) -> None:
        schema = get_schema_info()
        assert "customers" in schema
        assert "products" in schema
        assert "orders" in schema
        assert "order_items" in schema
        assert "employees" in schema

    def test_schema_has_columns(self) -> None:
        schema = get_schema_info()
        assert len(schema["customers"]["columns"]) > 0
        assert schema["customers"]["row_count"] > 0

    def test_primary_key_detected(self) -> None:
        schema = get_schema_info()
        pk_cols = [c for c in schema["products"]["columns"] if c["primary_key"]]
        assert len(pk_cols) >= 1
        assert pk_cols[0]["name"] == "id"
