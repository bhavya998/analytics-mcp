"""Shared fixtures — ensure database is initialized before tests."""

from __future__ import annotations

import pytest

from analytics_mcp.database import init_database


@pytest.fixture(scope="session", autouse=True)
def setup_database() -> None:
    """Initialize the database once for the entire test session."""
    init_database()
