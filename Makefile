.PHONY: install serve serve-http init inspect test lint clean

install:
	uv sync

serve:
	uv run analytics-mcp serve

serve-http:
	uv run analytics-mcp serve --transport http --port 8000

init:
	uv run analytics-mcp init

inspect:
	uv run analytics-mcp inspect

test:
	uv run pytest -v

lint:
	uv run ruff check src tests

clean:
	rm -rf .pytest_cache .ruff_cache data/*.db
