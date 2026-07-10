"""Pydantic models for structured tool outputs.

These define the outputSchema for each MCP tool, giving clients
machine-readable, validated structured content.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class QueryResult(BaseModel):
    """Result of a SQL query."""

    columns: list[str] = Field(description="Column names in result order")
    rows: list[dict[str, object]] = Field(description="Result rows as dicts")
    row_count: int = Field(description="Number of rows returned")


class RevenueSummary(BaseModel):
    """Revenue aggregated by a dimension."""

    dimension: str = Field(description="Grouping dimension value (e.g., 'Electronics' or 'Europe')")
    total_revenue: float = Field(description="Total revenue")
    order_count: int = Field(description="Number of orders")
    avg_order_value: float = Field(description="Average order value")
    total_profit: float = Field(description="Estimated profit (revenue - cost)")


class RevenueReport(BaseModel):
    """Full revenue report across a dimension."""

    group_by: str = Field(description="Dimension used for grouping")
    period_start: str = Field(description="Report period start date")
    period_end: str = Field(description="Report period end date")
    grand_total: float = Field(description="Total revenue across all groups")
    segments: list[RevenueSummary] = Field(description="Revenue breakdown by group")


class CustomerProfile(BaseModel):
    """360-degree customer view."""

    customer_id: int
    name: str
    email: str
    company: str
    region: str
    tier: str
    signup_date: str
    lifetime_value: float
    total_orders: int
    completed_orders: int
    avg_order_value: float
    favorite_category: str = Field(description="Product category with most purchases")
    recent_orders: list[dict[str, object]] = Field(description="Last 5 orders")


class ProductRanking(BaseModel):
    """A single product's ranking entry."""

    rank: int
    product_id: int
    product_name: str
    category: str
    metric_value: float = Field(description="Value of the ranking metric (revenue or quantity)")
    order_count: int


class TopProductsReport(BaseModel):
    """Top products leaderboard."""

    metric: str = Field(description="Ranking metric: 'revenue' or 'quantity'")
    limit: int
    products: list[ProductRanking]


class TrendPoint(BaseModel):
    """A single data point in a trend analysis."""

    period: str = Field(description="Time period label")
    revenue: float
    order_count: int
    growth_pct: float = Field(description="Period-over-period growth percentage")


class TrendAnalysis(BaseModel):
    """Sales trend over time."""

    granularity: str = Field(description="Time grouping: 'month' or 'quarter'")
    trend: list[TrendPoint]
    overall_growth_pct: float = Field(description="First-to-last period growth")
    peak_period: str = Field(description="Best performing period")


class RegionalPerformance(BaseModel):
    """Regional sales performance summary."""

    region: str
    total_revenue: float
    order_count: int
    customer_count: int
    avg_order_value: float
    rank: int = Field(description="Revenue rank among all regions (1 = highest)")


class RegionalReport(BaseModel):
    """Ranked regional performance report."""

    regions: list[RegionalPerformance]
    total_revenue: float = Field(description="Sum across all regions")
