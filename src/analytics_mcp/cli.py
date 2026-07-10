"""CLI entry point for analytics-mcp server."""

from __future__ import annotations

import typer
from rich.console import Console

app = typer.Typer(help="Enterprise Analytics MCP Server", no_args_is_help=True)
console = Console()


@app.command()
def serve(
    transport: str = typer.Option("stdio", "--transport", "-t", help="Transport: 'stdio' or 'http'"),
    host: str = typer.Option("0.0.0.0", help="HTTP bind address"),
    port: int = typer.Option(8000, help="HTTP bind port"),
) -> None:
    """Start the MCP server (stdio for local clients, http for remote)."""
    from analytics_mcp.database import init_database

    console.print("[cyan]Initializing database...[/cyan]")
    init_database()
    console.print("[green]Database ready.[/green]")

    from analytics_mcp.server import mcp

    if transport == "http":
        console.print(f"[cyan]Starting MCP server on HTTP {host}:{port}[/cyan]")
        mcp.run(transport="http", host=host, port=port)
    else:
        console.print("[cyan]Starting MCP server on stdio[/cyan]")
        mcp.run()


@app.command()
def init(
    force: bool = typer.Option(False, "--force", help="Force re-seed all data"),
) -> None:
    """Initialize or re-seed the database."""
    from analytics_mcp.database import init_database

    path = init_database(force_reseed=force)
    console.print(f"[green]Database initialized at: {path}[/green]")


@app.command()
def inspect() -> None:
    """List all registered tools, resources, and prompts."""
    import asyncio

    from analytics_mcp.server import mcp

    async def _list() -> None:
        console.print("\n[bold cyan]TOOLS:[/bold cyan]")
        tools = await mcp.list_tools()
        for tool in tools:
            desc = (tool.description or "")[:80]
            console.print(f"  - {tool.name}: {desc}")

        console.print("\n[bold cyan]RESOURCES:[/bold cyan]")
        resources = await mcp.list_resources()
        for resource in resources:
            console.print(f"  - {resource.uri}")

        console.print("\n[bold cyan]PROMPTS:[/bold cyan]")
        prompts = await mcp.list_prompts()
        for prompt in prompts:
            desc = (prompt.description or "")[:80]
            console.print(f"  - {prompt.name}: {desc}")

    asyncio.run(_list())


if __name__ == "__main__":
    app()
