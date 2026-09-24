# syntax=docker/dockerfile:1

# Build stage: resolves/installs deps with uv, then the project itself,
# in two separate `uv sync` layers so an app-code-only change doesn't
# invalidate the (slow) dependency-install layer.
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim AS builder
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
COPY pyproject.toml uv.lock ./
RUN uv sync --no-dev --no-install-project
COPY . .
RUN uv sync --no-dev

# Runtime stage: no uv, no build toolchain, just the venv the builder
# stage produced -- keeps the shipped image small.
FROM python:3.13-slim-bookworm
WORKDIR /app

# Runs as a non-root user; HOME is the same persistent volume the SQLite
# DB lives in, so the encrypted-credential file (docs/TASKS.md T143,
# `app/config/keyring_setup.py`) survives container recreation the same
# way the DB does.
RUN groupadd -r learningos \
    && useradd -r -g learningos -d /data learningos \
    && mkdir -p /data \
    && chown -R learningos:learningos /data

COPY --from=builder --chown=learningos:learningos /app /app

ENV PATH="/app/.venv/bin:$PATH" \
    HOME=/data \
    LEARNINGOS_DB_PATH=/data/learning_os.sqlite3

USER learningos
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/v1/health', timeout=2)" || exit 1

# alembic upgrade head is idempotent (docs/AGENTS.md #8: migrations, never
# ad-hoc schema changes) -- safe to run on every container start, not just
# the first one, so a new image with new migrations just works on restart.
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port 8000"]
