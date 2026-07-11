FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY src/ src/

ENV PYTHONPATH=/app/src
EXPOSE 8000

CMD ["uv", "run", "analytics-mcp", "serve", "--transport", "http", "--port", "8000"]
