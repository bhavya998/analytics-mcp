# ADR: Architecture Decision Record — analytics-mcp

## Status
Accepted

## Context
Build a production-grade MCP (Model Context Protocol) server that exposes enterprise sales analytics to any MCP-compatible AI client (Claude, OpenCode, Cursor). Must use the latest 2026 MCP patterns, not rookie-level tooling.

## Decisions

### D1: FastMCP 3.4 over Raw MCP SDK
**Decision:** Use the standalone `fastmcp==3.4.4` package (Prefect) rather than the official `mcp` SDK's bundled FastMCP.

**Rationale:** FastMCP 3.x has the most features (structured outputs, tool annotations, dependency injection, lifespan management), is the most actively developed, and powers the majority of production MCP servers. The official SDK's bundled copy lags behind. We pin with exact version to avoid breakage from the imminent v2 rewrite.

**Alternatives considered:**
- Official `mcp[cli]>=1.28`: stable but fewer features, slower updates
- `mcp==2.0.0b1`: explicitly marked "do not use in production" by authors
- Raw JSON-RPC implementation: reinventing the wheel

**Tradeoffs:** FastMCP is a third-party dependency (Prefect). If they change direction, we migrate. The abstraction is clean enough that switching to the official SDK later is straightforward.

### D2: Structured Outputs (Pydantic) on Every Tool
**Decision:** Every tool returns a typed Pydantic model (`RevenueReport`, `CustomerProfile`, `TrendAnalysis`, etc.) that becomes the tool's `outputSchema`.

**Rationale:** Structured outputs give clients machine-readable, validated responses — not just text blobs. Claude/OpenCode can render tables, charts, and forms from structured data. This is a 2026 MCP best practice enabled by the `2025-06-18` spec revision.

### D3: Tool Annotations (readOnlyHint)
**Decision:** All 6 tools are annotated with `readOnlyHint: True`.

**Rationale:** Clients like Claude Desktop and ChatGPT skip confirmation prompts for read-only tools. This reduces friction — the user doesn't get "Allow query_database?" for every call. Also enables client-side caching and batching optimizations.

### D4: SQLite with Realistic Enterprise Schema
**Decision:** Seed SQLite with 200 customers, 25 products, 2000 orders, 5000+ order_items, 15 employees across 5 regions.

**Rationale:** Toy data (10 rows) doesn't exercise SQL aggregations meaningfully. 2000+ orders with varied statuses, tiers, and regions produces realistic revenue distributions, trend patterns, and regional differences — making demo queries actually interesting.

**Alternatives considered:**
- Real company data: privacy/legal concerns
- Random schema: doesn't tell a coherent business story
- PostgreSQL: adds deployment complexity for no benefit at this scale

### D5: In-Memory Client Testing (No Ports)
**Decision:** Test via `Client(mcp)` in-memory — no subprocess, no port binding, no transport overhead.

**Rationale:** This is the modern 2026 testing pattern recommended by the FastMCP team. It's era-neutral (works with both 2025 and 2026 spec eras), faster than transport-based tests, and eliminates port flakiness in CI. The `raise_exceptions=True` flag surfaces server-side errors directly.

**Alternatives considered:**
- Subprocess + stdio transport: slow, flaky, hard to debug
- HTTP transport + requests: requires port management, race conditions
- Mock the tools directly: doesn't test the MCP protocol layer

### D6: Resources + Prompts (Not Just Tools)
**Decision:** Expose 3 resources (schema docs, table details, report templates) and 2 prompts (sales analysis, customer segmentation) alongside the 6 tools.

**Rationale:** Many MCP servers only expose tools. Adding resources lets clients introspect the database schema without trial-and-error. Prompts provide reusable analysis templates — the client can render them as quick actions. This demonstrates full MCP mastery.

### D7: SQL Injection Protection
**Decision:** The `query_database` tool only accepts SELECT statements, validated by checking `sql.strip().upper().startswith("SELECT")`.

**Tradeoffs:** This is a basic check — a sophisticated attacker could craft malicious SELECTs (e.g., `SELECT * FROM sqlite_master` to enumerate schema). For a portfolio project, this is acceptable. For production, add a SQL parser (e.g., `sqlglot`) to validate AST.

## Consequences
- Full MCP protocol compliance: tools, resources, prompts
- Any MCP client can connect and immediately analyze enterprise data
- 43 tests pass with zero port dependencies
- FastMCP 3.4 gives us structured outputs, annotations, and modern testing for free
