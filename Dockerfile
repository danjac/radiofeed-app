ARG PYTHON_BASE=3.12.4-bookworm

# Production Dockerfile for application

FROM node:22-bookworm-slim AS frontend-deps

WORKDIR /app

# Asset requirements

COPY package*.json ./

RUN npm install

# Build assets

COPY . /app

ENV NODE_ENV=production

RUN npm run build && rm -rf node_modules

# Python

FROM python:$PYTHON_BASE AS backend-deps

ENV PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=random \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONFAULTHANDLER=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DEFAULT_TIMEOUT=100 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_ROOT_USER_ACTION=ignore

WORKDIR /app

# Python requirements

RUN pip install pdm==2.18.1

COPY ./pyproject.toml /app/pyproject.toml

COPY ./pdm.lock /app/pdm.lock

RUN pdm install --check --prod --no-editable --no-self --fail-fast

FROM python:$PYTHON_BASE

WORKDIR /app

COPY . /app

COPY --from=backend-deps /app/.venv/ /app/.venv

ENV PATH="/app/.venv/bin:$PATH"

# Download NLTK files

COPY ./nltk.txt /app/nltk.txt

RUN xargs -I{} python -c "import nltk; nltk.download('{}')" < /app/nltk.txt

# Build and copy over assets

COPY --from=frontend-deps /app/assets /app/assets

# Collect static files for Whitenoise

RUN python manage.py collectstatic --no-input --traceback
