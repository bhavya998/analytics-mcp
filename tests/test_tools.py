"""Tests for MCP server tools — tests the tool functions directly.

For full MCP client integration tests, see test_server_client.py.
"""

from __future__ import annotations

import pytest

from analytics_mcp.server import (
    analyze_sales_trend,
    get_customer_profile,
    get_regional_performance,
    get_revenue_report,
    get_top_products,
    query_database,
)


class TestQueryDatabase:
    def test_basic_select(self) -> None:
        result = query_database("SELECT * FROM products LIMIT 3")
        assert result.row_count == 3
        assert len(result.rows) == 3
        assert "name" in result.columns

    def test_aggregate(self) -> None:
        result = query_database("SELECT COUNT(*) as total FROM orders")
        assert result.row_count == 1
        assert result.rows[0]["total"] > 0

    def test_rejects_non_select(self) -> None:
        with pytest.raises(ValueError):
            query_database("UPDATE products SET price = 0")


class TestRevenueReport:
    def test_by_category(self) -> None:
        report = get_revenue_report(group_by="category")
        assert report.group_by == "category"
        assert len(report.segments) > 0
        assert report.grand_total > 0
        assert all(s.total_revenue > 0 for s in report.segments)

    def test_by_region(self) -> None:
        report = get_revenue_report(group_by="region")
        assert len(report.segments) == 5

    def test_by_tier(self) -> None:
        report = get_revenue_report(group_by="tier")
        assert len(report.segments) <= 3

    def test_invalid_group_raises(self) -> None:
        with pytest.raises(ValueError):
            get_revenue_report(group_by="invalid")

    def test_date_range(self) -> None:
        report = get_revenue_report(group_by="category", period_start="2024-06-01", period_end="2024-12-31")
        assert report.period_start == "2024-06-01"


class TestCustomerProfile:
    def test_valid_customer(self) -> None:
        profile = get_customer_profile(customer_id=1)
        assert profile.customer_id == 1
        assert len(profile.name) > 0
        assert profile.total_orders > 0
        assert profile.avg_order_value > 0

    def test_nonexistent_customer(self) -> None:
        with pytest.raises(ValueError, match="not found"):
            get_customer_profile(customer_id=99999)

    def test_has_recent_orders(self) -> None:
        profile = get_customer_profile(customer_id=1)
        assert isinstance(profile.recent_orders, list)


class TestTopProducts:
    def test_by_revenue(self) -> None:
        report = get_top_products(metric="revenue", limit=5)
        assert len(report.products) == 5
        assert report.products[0].rank == 1
        assert report.products[0].metric_value >= report.products[-1].metric_value

    def test_by_quantity(self) -> None:
        report = get_top_products(metric="quantity", limit=3)
        assert report.metric == "quantity"
        assert all(p.metric_value > 0 for p in report.products)

    def test_filter_by_category(self) -> None:
        report = get_top_products(metric="revenue", limit=10, category="Electronics")
        assert all(p.category == "Electronics" for p in report.products)


class TestSalesTrend:
    def test_monthly(self) -> None:
        trend = analyze_sales_trend(granularity="month")
        assert trend.granularity == "month"
        assert len(trend.trend) > 0
        assert all(p.revenue > 0 for p in trend.trend)

    def test_quarterly(self) -> None:
        trend = analyze_sales_trend(granularity="quarter")
        assert trend.granularity == "quarter"
        assert len(trend.trend) > 0

    def test_growth_calculated(self) -> None:
        trend = analyze_sales_trend(granularity="month")
        if len(trend.trend) >= 2:
            assert isinstance(trend.trend[1].growth_pct, float)

    def test_peak_period(self) -> None:
        trend = analyze_sales_trend(granularity="month")
        assert len(trend.peak_period) > 0


class TestRegionalPerformance:
    def test_all_regions_present(self) -> None:
        report = get_regional_performance()
        assert len(report.regions) == 5
        regions = [r.region for r in report.regions]
        assert "North America" in regions
        assert "Europe" in regions

    def test_ranked_by_revenue(self) -> None:
        report = get_regional_performance()
        for i in range(len(report.regions) - 1):
            assert report.regions[i].total_revenue >= report.regions[i + 1].total_revenue

    def test_ranks_start_at_1(self) -> None:
        report = get_regional_performance()
        assert report.regions[0].rank == 1
