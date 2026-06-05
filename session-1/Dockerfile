FROM python:3.14-slim

# Install uv by copying its static binary from the official uv image.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Install dependencies first (separate layer = better build caching).
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev

# Copy the application code.
COPY . .

EXPOSE 8000

# Shell form so $PORT (provided by Render) expands; falls back to 8000 locally.
CMD uv run uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
