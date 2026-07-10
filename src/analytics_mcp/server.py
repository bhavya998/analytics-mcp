"""Production-grade MCP server for enterprise sales analytics.

Exposes 6 tools, 3 resources, and 2 prompts over a SQLite database.
Built with FastMCP 3.x — supports stdio and HTTP transports.

Usage:
    analytics-mcp serve          # stdio (for Claude Desktop, OpenCode, Cursor)
    analytics-mcp serve --http   # HTTP transport (port 8000)
"""

from __future__ import annotations

from typing import Annotated

from fastmcp import FastMCP
from pydantic import Field

from analytics_mcp.database import get_schema_info, init_database, query_db
from analytics_mcp.schemas import (
    CustomerProfile,
    ProductRanking,
    QueryResult,
    RegionalPerformance,
    RegionalReport,
    RevenueReport,
    RevenueSummary,
    TopProductsReport,
    TrendAnalysis,
    TrendPoint,
)

mcp = FastMCP(
    "Enterprise Analytics",
    mask_error_details=True,
    on_duplicate="error",
)


# ──────────────────────────────────────────────────────────────────────────────
# TOOLS
# ──────────────────────────────────────────────────────────────────────────────


@mcp.tool(annotations={"readOnlyHint": True})
def query_database(
    sql: Annotated[str, Field(description="SELECT SQL query to execute. Only SELECT statements allowed.")],
) -> QueryResult:
    """Run a read-only SQL query against the enterprise database.

    Tables: customers, products, orders, order_items, employees.

    Examples:
        SELECT * FROM customers WHERE tier = 'enterprise' LIMIT 10
        SELECT region, COUNT(*) as customers FROM customers GROUP BY region
        SELECT p.name, SUM(oi.quantity) as sold FROM order_items oi
          JOIN products p ON oi.product_id = p.id GROUP BY p.name ORDER BY sold DESC LIMIT 5
    """
    rows = query_db(sql)
    columns = list(rows[0].keys()) if rows else []
    return QueryResult(columns=columns, rows=rows, row_count=len(rows))


@mcp.tool(annotations={"readOnlyHint": True})
def get_revenue_report(
    group_by: Annotated[
        str,
        Field(description="Dimension to group by: 'category', 'region', 'tier', 'status', or 'month'"),
    ] = "category",
    period_start: Annotated[str, Field(description="Start date YYYY-MM-DD (default: 2024-01-01)")] = "2024-01-01",
    period_end: Annotated[str, Field(description="End date YYYY-MM-DD (default: 2025-06-30)")] = "2025-06-30",
) -> RevenueReport:
    """Generate a revenue report grouped by a dimension within a date range.

    Returns total revenue, order count, average order value, and estimated profit per segment.
    """
    valid_groups = {"category", "region", "tier", "status", "month"}
    if group_by not in valid_groups:
        raise ValueError(f"group_by must be one of {valid_groups}")

    if group_by == "category":
        dimension_col = "p.category"
        join_clause = "JOIN order_items oi ON o.id = oi.order_id JOIN products p ON oi.product_id = p.id"
        profit_expr = "SUM(oi.quantity * (oi.unit_price - p.cost))"
    elif group_by == "region":
        dimension_col = "c.region"
        join_clause = "JOIN customers c ON o.customer_id = c.id"
        profit_expr = "SUM(o.total * 0.4)"
    elif group_by == "tier":
        dimension_col = "c.tier"
        join_clause = "JOIN customers c ON o.customer_id = c.id"
        profit_expr = "SUM(o.total * 0.4)"
    elif group_by == "status":
        dimension_col = "o.status"
        join_clause = ""
        profit_expr = "SUM(o.total * 0.4)"
    else:
        dimension_col = "strftime('%Y-%m', o.order_date)"
        join_clause = ""
        profit_expr = "SUM(o.total * 0.4)"

    sql = f"""
        SELECT
            {dimension_col} as dimension,
            SUM(o.total) as total_revenue,
            COUNT(*) as order_count,
            AVG(o.total) as avg_order_value,
            {profit_expr} as total_profit
        FROM orders o
        {join_clause}
        WHERE o.order_date BETWEEN ? AND ?
        GROUP BY {dimension_col}
        ORDER BY total_revenue DESC
    """

    rows = query_db(sql, (period_start, period_end))
    segments = [
        RevenueSummary(
            dimension=str(r["dimension"]),
            total_revenue=round(r["total_revenue"] or 0, 2),
            order_count=r["order_count"],
            avg_order_value=round(r["avg_order_value"] or 0, 2),
            total_profit=round(r["total_profit"] or 0, 2),
        )
        for r in rows
    ]
    grand_total = sum(s.total_revenue for s in segments)

    return RevenueReport(
        group_by=group_by,
        period_start=period_start,
        period_end=period_end,
        grand_total=round(grand_total, 2),
        segments=segments,
    )


@mcp.tool(annotations={"readOnlyHint": True})
def get_customer_profile(
    customer_id: Annotated[int, Field(description="Customer ID to profile", ge=1)],
) -> CustomerProfile:
    """Get a 360-degree customer view: profile, order history, spending stats, favorite category.

    Useful for account reviews, churn analysis, and upsell identification.
    """
    customers = query_db("SELECT * FROM customers WHERE id = ?", (customer_id,))
    if not customers:
        raise ValueError(f"Customer {customer_id} not found")

    c = customers[0]

    stats = query_db(
        """
        SELECT
            COUNT(*) as total_orders,
            SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
            AVG(total) as avg_order
        FROM orders WHERE customer_id = ?
        """,
        (customer_id,),
    )[0]

    fav = query_db(
        """
        SELECT p.category, SUM(oi.quantity) as qty
        FROM order_items oi
        JOIN orders o ON oi.order_id = o.id
        JOIN products p ON oi.product_id = p.id
        WHERE o.customer_id = ?
        GROUP BY p.category ORDER BY qty DESC LIMIT 1
        """,
        (customer_id,),
    )
    favorite = fav[0]["category"] if fav else "N/A"

    recent = query_db(
        """
        SELECT o.id, o.order_date, o.status, o.total,
               COUNT(oi.id) as item_count
        FROM orders o LEFT JOIN order_items oi ON o.id = oi.order_id
        WHERE o.customer_id = ?
        GROUP BY o.id ORDER BY o.order_date DESC LIMIT 5
        """,
        (customer_id,),
    )

    return CustomerProfile(
        customer_id=c["id"],
        name=c["name"],
        email=c["email"],
        company=c["company"],
        region=c["region"],
        tier=c["tier"],
        signup_date=c["signup_date"],
        lifetime_value=round(c["lifetime_value"] or 0, 2),
        total_orders=stats["total_orders"] or 0,
        completed_orders=stats["completed"] or 0,
        avg_order_value=round(stats["avg_order"] or 0, 2),
        favorite_category=favorite,
        recent_orders=recent,
    )


@mcp.tool(annotations={"readOnlyHint": True})
def get_top_products(
    metric: Annotated[
        str,
        Field(description="Ranking metric: 'revenue' or 'quantity'"),
    ] = "revenue",
    limit: Annotated[int, Field(description="Number of top products to return", ge=1, le=50)] = 10,
    category: Annotated[
        str | None,
        Field(description="Filter by product category (optional)"),
    ] = None,
) -> TopProductsReport:
    """Get a leaderboard of top-performing products by revenue or quantity sold.

    Optionally filter by category.
    """
    metric_col = "SUM(oi.quantity * oi.unit_price)" if metric == "revenue" else "SUM(oi.quantity)"
    cat_filter = "AND p.category = ?" if category else ""
    params: tuple = () if not category else (category,)

    rows = query_db(
        f"""
        SELECT
            p.id, p.name, p.category,
            {metric_col} as metric_value,
            COUNT(DISTINCT oi.order_id) as order_count
        FROM order_items oi
        JOIN products p ON oi.product_id = p.id
        WHERE 1=1 {cat_filter}
        GROUP BY p.id, p.name, p.category
        ORDER BY metric_value DESC
        LIMIT ?
        """,
        params + (limit,),
    )

    products = [
        ProductRanking(
            rank=i + 1,
            product_id=r["id"],
            product_name=r["name"],
            category=r["category"],
            metric_value=round(r["metric_value"] or 0, 2),
            order_count=r["order_count"],
        )
        for i, r in enumerate(rows)
    ]

    return TopProductsReport(metric=metric, limit=limit, products=products)


@mcp.tool(annotations={"readOnlyHint": True})
def analyze_sales_trend(
    granularity: Annotated[
        str,
        Field(description="Time grouping: 'month' or 'quarter'"),
    ] = "month",
    period_start: Annotated[str, Field(description="Start date YYYY-MM-DD")] = "2024-01-01",
    period_end: Annotated[str, Field(description="End date YYYY-MM-DD")] = "2025-06-30",
) -> TrendAnalysis:
    """Analyze sales trends over time with period-over-period growth rates.

    Returns revenue, order count, and growth percentage for each period.
    """
    if granularity == "quarter":
        sql_expr = "strftime('%Y-Q', o.order_date) || ((CAST(strftime('%m', o.order_date) AS INTEGER) - 1) / 3 + 1)"
    else:
        sql_expr = "strftime('%Y-%m', o.order_date)"

    rows = query_db(
        f"""
        SELECT
            {sql_expr} as period,
            SUM(o.total) as revenue,
            COUNT(*) as order_count
        FROM orders o
        WHERE o.order_date BETWEEN ? AND ? AND o.status = 'completed'
        GROUP BY {sql_expr}
        ORDER BY period ASC
        """,
        (period_start, period_end),
    )

    points: list[TrendPoint] = []
    prev_revenue: float | None = None
    for r in rows:
        revenue = round(r["revenue"] or 0, 2)
        growth = 0.0
        if prev_revenue and prev_revenue > 0:
            growth = round((revenue - prev_revenue) / prev_revenue * 100, 2)
        points.append(
            TrendPoint(
                period=r["period"],
                revenue=revenue,
                order_count=r["order_count"],
                growth_pct=growth,
            )
        )
        prev_revenue = revenue

    if not points:
        raise ValueError("No data found for the specified period range")

    overall = 0.0
    if len(points) >= 2 and points[0].revenue > 0:
        overall = round((points[-1].revenue - points[0].revenue) / points[0].revenue * 100, 2)

    peak = max(points, key=lambda p: p.revenue).period

    return TrendAnalysis(
        granularity=granularity,
        trend=points,
        overall_growth_pct=overall,
        peak_period=peak,
    )


@mcp.tool(annotations={"readOnlyHint": True})
def get_regional_performance() -> RegionalReport:
    """Get ranked sales performance by region: revenue, orders, customers, AOV.

    Returns all 5 regions ranked by total revenue.
    """
    rows = query_db(
        """
        SELECT
            c.region,
            SUM(o.total) as total_revenue,
            COUNT(DISTINCT o.id) as order_count,
            COUNT(DISTINCT o.customer_id) as customer_count,
            AVG(o.total) as avg_order_value
        FROM orders o
        JOIN customers c ON o.customer_id = c.id
        WHERE o.status = 'completed'
        GROUP BY c.region
        ORDER BY total_revenue DESC
        """
    )

    regions = [
        RegionalPerformance(
            region=r["region"],
            total_revenue=round(r["total_revenue"] or 0, 2),
            order_count=r["order_count"],
            customer_count=r["customer_count"],
            avg_order_value=round(r["avg_order_value"] or 0, 2),
            rank=i + 1,
        )
        for i, r in enumerate(rows)
    ]

    total = sum(r.total_revenue for r in regions)
    return RegionalReport(regions=regions, total_revenue=round(total, 2))


# ──────────────────────────────────────────────────────────────────────────────
# RESOURCES
# ──────────────────────────────────────────────────────────────────────────────


@mcp.resource("schema://database")
def database_schema() -> str:
    """Full database schema: all tables, columns, types, and row counts."""
    schema = get_schema_info()
    lines = ["# Enterprise Database Schema\n"]
    for table_name, info in schema.items():
        lines.append(f"\n## {table_name} ({info['row_count']} rows)\n")
        lines.append("| Column | Type | Nullable | PK |")
        lines.append("|--------|------|----------|----|")
        for col in info["columns"]:
            pk = "YES" if col["primary_key"] else ""
            lines.append(f"| {col['name']} | {col['type']} | {'YES' if col['nullable'] else 'NO'} | {pk} |")
    return "\n".join(lines)


@mcp.resource("schema://tables/{table_name}")
def table_schema(table_name: str) -> str:
    """Detailed schema for a specific table including sample rows."""
    schema = get_schema_info()
    if table_name not in schema:
        raise ValueError(f"Table '{table_name}' not found. Available: {list(schema.keys())}")

    info = schema[table_name]
    lines = [f"# Table: {table_name}\n", f"**Rows:** {info['row_count']}\n", "## Columns\n"]
    for col in info["columns"]:
        pk = " (PK)" if col["primary_key"] else ""
        lines.append(f"- `{col['name']}` ({col['type']}, {'nullable' if col['nullable'] else 'NOT NULL'}){pk}")

    sample = query_db(f"SELECT * FROM {table_name} LIMIT 3")
    if sample:
        lines.append("\n## Sample Data\n")
        for row in sample:
            lines.append(f"- {dict(row)}")

    return "\n".join(lines)


@mcp.resource("report://templates")
def report_templates() -> str:
    """Available report templates and their descriptions."""
    return """# Available Report Templates

## Revenue Reports
- **By Category**: `get_revenue_report(group_by='category')`
- **By Region**: `get_revenue_report(group_by='region')`
- **By Customer Tier**: `get_revenue_report(group_by='tier')`
- **Monthly Trend**: `get_revenue_report(group_by='month')`

## Product Analytics
- **Top Sellers**: `get_top_products(metric='revenue', limit=10)`
- **Most Ordered**: `get_top_products(metric='quantity', limit=10)`
- **Category Leaders**: `get_top_products(metric='revenue', category='Electronics')`

## Customer Insights
- **Profile**: `get_customer_profile(customer_id=42)`
- **Enterprise Tier**: `query_database("SELECT * FROM customers WHERE tier='enterprise'")`

## Trend Analysis
- **Monthly**: `analyze_sales_trend(granularity='month')`
- **Quarterly**: `analyze_sales_trend(granularity='quarter')`

## Regional Performance
- **Ranked**: `get_regional_performance()`
"""


# ──────────────────────────────────────────────────────────────────────────────
# PROMPTS
# ──────────────────────────────────────────────────────────────────────────────


@mcp.prompt()
def sales_analysis(focus: str = "overall") -> str:
    """Generate a comprehensive sales analysis prompt for the LLM.

    Args:
        focus: Area to focus on — 'overall', 'category', 'region', or 'customer'.
    """
    return f"""You are a senior sales analyst. Using the enterprise analytics MCP tools,
provide a comprehensive {focus} sales analysis:

1. Start with overall revenue summary using get_revenue_report
2. Identify top 5 products using get_top_products
3. Analyze the monthly trend using analyze_sales_trend
4. Rank regional performance using get_regional_performance
5. Highlight 3 key insights and 2 actionable recommendations

Focus area: {focus}
"""


@mcp.prompt()
def customer_segmentation() -> str:
    """Generate a customer segmentation analysis prompt."""
    return """You are a customer success strategist. Using the enterprise analytics MCP tools:

1. Query customers by tier and region using query_database
2. Get detailed profiles for 3 enterprise customers using get_customer_profile
3. Identify customers with high lifetime_value but low recent activity
4. Segment customers into: Champions, At Risk, New, Dormant
5. Recommend retention strategies for each segment

Use the database schema resource for column references.
"""


# ──────────────────────────────────────────────────────────────────────────────
# INIT
# ──────────────────────────────────────────────────────────────────────────────


def ensure_database() -> None:
    """Initialize the database on startup if it doesn't exist."""
    init_database()
