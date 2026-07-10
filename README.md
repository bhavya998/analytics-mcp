<div align="center">

# analytics-mcp

**Production-grade MCP server for enterprise sales analytics. 6 tools, 3 resources, 2 prompts — all with structured outputs — over a SQLite database. Connects to Claude, OpenCode, Cursor, and any MCP client.**

[![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)](https://python.org)
[![FastMCP](https://img.shields.io/badge/FastMCP-3.4-6366f1)](https://gofastmcp.com)
[![Tests](https://img.shields.io/badge/Tests-43%20passing-22c55e)]()
[![License](https://img.shields.io/badge/License-MIT-22c55e)](LICENSE)

</div>

---

## What This Is

A Model Context Protocol (MCP) server that exposes an enterprise sales database to LLM clients. Instead of copy-pasting data into ChatGPT, connect this server and let the AI query, analyze, and visualize your data through structured tools.

**Built with the latest MCP patterns (July 2026):**
- **FastMCP 3.4** — high-level server framework
- **Structured outputs** — Pydantic models define `outputSchema` for every tool
- **Tool annotations** — `readOnlyHint` lets clients skip confirmations
- **In-memory client testing** — no port flakiness, era-neutral
- **Resources** — schema introspection, table details, report templates
- **Prompts** — reusable analysis templates (sales analysis, customer segmentation)
- **Both transports** — stdio (local) + HTTP (remote)

---

## Quick Start

```bash
git clone https://github.com/bhavya998/analytics-mcp.git
cd analytics-mcp
uv sync

# Initialize database (200 customers, 25 products, 2000 orders)
uv run analytics-mcp init

# Start server (stdio for local MCP clients)
uv run analytics-mcp serve

# Or HTTP transport for remote access
uv run analytics-mcp serve --transport http --port 8000
```

### Connect to Claude Desktop / OpenCode

Add to your MCP client config:

```json
{
  "mcpServers": {
    "analytics": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/analytics-mcp", "analytics-mcp", "serve"]
    }
  }
}
```

Then ask: *"Show me the top 5 products by revenue and analyze the monthly sales trend"*

---

## Tools

| Tool | Description | Annotations |
|---|---|---|
| `query_database` | Run parameterized SELECT queries against the database | `readOnlyHint` |
| `get_revenue_report` | Revenue by category/region/tier/status/month with profit analysis | `readOnlyHint` |
| `get_customer_profile` | 360-degree customer view: orders, LTV, favorite category, recent activity | `readOnlyHint` |
| `get_top_products` | Leaderboard by revenue or quantity, optional category filter | `readOnlyHint` |
| `analyze_sales_trend` | Time-series with period-over-period growth rates | `readOnlyHint` |
| `get_regional_performance` | Ranked regional performance with revenue, orders, customers, AOV | `readOnlyHint` |

## Resources

| URI | Description |
|---|---|
| `schema://database` | Full database schema (all tables, columns, types, row counts) |
| `schema://tables/{table_name}` | Detailed table schema with sample rows |
| `report://templates` | Available report templates and usage examples |

## Prompts

| Prompt | Description |
|---|---|
| `sales_analysis` | Comprehensive sales analysis with focus area (overall/category/region/customer) |
| `customer_segmentation` | Segment customers into Champions/At Risk/New/Dormant with retention strategies |

---

## Database Schema

```
customers (200 rows)
  id, name, email, company, region, tier, signup_date, lifetime_value

products (25 rows)
  id, name, category, price, cost, stock

orders (2000 rows)
  id, customer_id, employee_id, order_date, status, total

order_items (5000+ rows)
  id, order_id, product_id, quantity, unit_price

employees (15 rows)
  id, name, role, region, hire_date
```

---

## Testing

```bash
make test         # 43 tests: database, tools, full MCP client integration
make lint         # ruff
```

| Suite | Tests | Pattern |
|---|---|---|
| `test_database.py` | 8 | DB init, query validation, schema introspection |
| `test_tools.py` | 17 | Direct tool function calls (all 6 tools) |
| `test_server_client.py` | 12 | Full MCP protocol via in-memory Client |

Tests use the **modern in-memory `Client(mcp)` pattern** — no ports, no subprocesses, era-neutral.

---

## Tech Stack

| Layer | Technology |
|---|---|
| MCP Framework | FastMCP 3.4 (Prefect) |
| Protocol | MCP 1.28 (Streamable HTTP + stdio) |
| Database | SQLite with seeded enterprise data |
| Validation | Pydantic v2 (structured tool outputs) |
| CLI | Typer + Rich |
| Testing | pytest + pytest-asyncio + FastMCP Client |

## Project Structure

```
analytics-mcp/
├── src/analytics_mcp/
│   ├── server.py         MCP server: 6 tools, 3 resources, 2 prompts
│   ├── database.py       SQLite setup + schema + seed data (2000+ orders)
│   ├── schemas.py        Pydantic models for structured outputs
│   └── cli.py            CLI (serve, init, inspect)
├── tests/                43 tests (database, tools, client integration)
├── data/                 SQLite database (auto-generated, gitignored)
├── Makefile
└── pyproject.toml
```

## License

MIT
