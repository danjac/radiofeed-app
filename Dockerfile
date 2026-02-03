ARG PYTHON_IMAGE=3.14.2-slim-bookworm

# Install Python dependencies
FROM python:${PYTHON_IMAGE} AS python-base
ENV LC_CTYPE=C.utf8 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=random \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONFAULTHANDLER=1 \
    UV_PROJECT_ENVIRONMENT="/app/.venv" \
    UV_PYTHON_INSTALL_DIR="/python" \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:$PATH"
WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:0.9.8 /uv /usr/local/bin/uv

# Install Python dependencies
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-group dev --no-install-project

# Download NLTK files
FROM python-base AS nltk-corpora
COPY nltk.txt ./
RUN --mount=type=cache,target=/root/.cache/uv \
    xargs -I{} uv run python -c "import nltk; nltk.download('{}')" < nltk.txt

# Build static assets
FROM python-base AS staticfiles
COPY . .
RUN --mount=type=cache,target=/root/.cache/uv \
    uv run python manage.py tailwind build && \
    uv run python manage.py tailwind remove_cli && \
    uv run python manage.py collectstatic --no-input

# Final production image
FROM python:${PYTHON_IMAGE} AS webapp
ENV LC_CTYPE=C.utf8 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=random \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH"

# Create non-root user FIRST, before any file copies
RUN useradd -m -u 1000 django

WORKDIR /app

# Copy files with correct ownership from the start using --chown
COPY --from=python-base --chown=django:django /app/.venv /app/.venv
COPY --from=nltk-corpora --chown=django:django /root/nltk_data /root/nltk_data
COPY --from=staticfiles --chown=django:django /app/staticfiles /app/staticfiles

# Copy application code with correct ownership
COPY --chown=django:django . .

USER django

CMD ["./entrypoint.sh"]
