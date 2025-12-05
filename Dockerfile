# Install Python dependencies
FROM python:3.14.1-slim-bookworm AS python-base

ENV LC_CTYPE=C.utf8 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=random \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONFAULTHANDLER=1 \
    UV_PROJECT_ENVIRONMENT="/app/.venv" \
    UV_PYTHON_INSTALL_DIR="/python" \
    UV_COMPILE_BYTECODE=1

WORKDIR /app

# Install uv

COPY --from=ghcr.io/astral-sh/uv:0.9.8 /uv /usr/local/bin/uv

# Install Python dependencies

COPY ./pyproject.toml ./uv.lock /app/

RUN uv sync --frozen --no-dev --no-install-project

ENV PATH="/app/.venv/bin:$PATH"

# Download NLTK files

FROM python-base AS nltk-corpora

COPY ./nltk.txt /app/

RUN xargs -I{} uv run python -c "import nltk; nltk.download('{}')" < /app/nltk.txt

# Build static assets

FROM python-base AS staticfiles

COPY . /app

RUN uv run python manage.py tailwind build && \
    uv run python manage.py tailwind remove_cli && \
    uv run python manage.py collectstatic --no-input

FROM python-base AS webapp

COPY --from=nltk-corpora /root/nltk_data /root/nltk_data
COPY --from=staticfiles /app/staticfiles /app/staticfiles

COPY . /app

# Remove any build dependencies to reduce image size

RUN rm -rf \
    /app/nltk.txt \
    /app/pyproject.toml \
    /app/tailwind \
    /app/uv.lock
