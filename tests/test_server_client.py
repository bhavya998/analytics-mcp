"""Full MCP client integration tests — in-memory, no port needed.

Uses the modern FastMCP Client pattern (2026) — connects to the server
in-memory, exercises the full protocol stack including serialization,
schema validation, and structured outputs.
"""

from __future__ import annotations

import pytest
from fastmcp import Client


@pytest.fixture
async def client():
    """Create an in-memory MCP client connected to our server."""
    from analytics_mcp.server import mcp

    async with Client(mcp) as c:
        yield c


class TestToolListing:
    @pytest.mark.asyncio
    async def test_lists_all_tools(self, client: Client) -> None:
        tools = await client.list_tools()
        tool_names = [t.name for t in tools]
        assert "query_database" in tool_names
        assert "get_revenue_report" in tool_names
        assert "get_customer_profile" in tool_names
        assert "get_top_products" in tool_names
        assert "analyze_sales_trend" in tool_names
        assert "get_regional_performance" in tool_names

    @pytest.mark.asyncio
    async def test_tools_have_descriptions(self, client: Client) -> None:
        tools = await client.list_tools()
        for tool in tools:
            assert tool.description is not None
            assert len(tool.description) > 10

    @pytest.mark.asyncio
    async def test_tools_have_input_schema(self, client: Client) -> None:
        tools = await client.list_tools()
        for tool in tools:
            assert tool.inputSchema is not None


class TestResourceListing:
    @pytest.mark.asyncio
    async def test_lists_resources(self, client: Client) -> None:
        resources = await client.list_resources()
        uris = [str(r.uri) for r in resources]
        assert any("schema://database" in uri for uri in uris)

    @pytest.mark.asyncio
    async def test_read_database_schema(self, client: Client) -> None:
        result = await client.read_resource("schema://database")
        content = str(result)
        assert "customers" in content
        assert "products" in content
        assert "orders" in content


class TestPromptListing:
    @pytest.mark.asyncio
    async def test_lists_prompts(self, client: Client) -> None:
        prompts = await client.list_prompts()
        prompt_names = [p.name for p in prompts]
        assert "sales_analysis" in prompt_names
        assert "customer_segmentation" in prompt_names

    @pytest.mark.asyncio
    async def test_render_sales_prompt(self, client: Client) -> None:
        result = await client.get_prompt("sales_analysis", {"focus": "region"})
        assert len(result.messages) > 0


class TestToolCalls:
    @pytest.mark.asyncio
    async def test_call_query_database(self, client: Client) -> None:
        result = await client.call_tool(
            "query_database",
            {"sql": "SELECT COUNT(*) as total FROM products"},
        )
        assert len(result.content) > 0
        text = result.content[0].text
        assert "25" in text or "total" in text

    @pytest.mark.asyncio
    async def test_call_revenue_report(self, client: Client) -> None:
        result = await client.call_tool(
            "get_revenue_report",
            {"group_by": "category"},
        )
        assert len(result.content) > 0

    @pytest.mark.asyncio
    async def test_call_regional_performance(self, client: Client) -> None:
        result = await client.call_tool("get_regional_performance", {})
        assert len(result.content) > 0

    @pytest.mark.asyncio
    async def test_call_top_products(self, client: Client) -> None:
        result = await client.call_tool(
            "get_top_products",
            {"metric": "revenue", "limit": 3},
        )
        assert len(result.content) > 0

    @pytest.mark.asyncio
    async def test_call_sales_trend(self, client: Client) -> None:
        result = await client.call_tool(
            "analyze_sales_trend",
            {"granularity": "month"},
        )
        assert len(result.content) > 0

    @pytest.mark.asyncio
    async def test_call_customer_profile(self, client: Client) -> None:
        result = await client.call_tool(
            "get_customer_profile",
            {"customer_id": 1},
        )
        assert len(result.content) > 0
