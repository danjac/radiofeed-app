# Production Dockerfile for application

FROM node:22-bookworm-slim AS frontend

WORKDIR /app

# Asset requirements

COPY package*.json ./

RUN npm install

# Build assets

COPY . /app

ENV NODE_ENV=production

RUN npm run build

# Python

FROM python:3.12.4-bookworm AS backend

ENV PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=random \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONFAULTHANDLER=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DEFAULT_TIMEOUT=100 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_ROOT_USER_ACTION=ignore \
    POETRY_NO_INTERACTION=true \
    POETRY_VIRTUALENVS_IN_PROJECT=false \
    POETRY_VIRTUALENVS_CREATE=false \
    POETRY_CACHE_DIR=/tmp/poetry_cache

WORKDIR /app

# Python requirements

RUN pip install poetry==1.8.3

COPY ./pyproject.toml /app/pyproject.toml

COPY ./poetry.lock /app/poetry.lock

RUN poetry install --without=dev --no-root && rm -rf $POETRY_CACHE_DIR

# Download NLTK files

COPY ./nltk.txt /app/nltk.txt

RUN xargs -I{} python -c "import nltk; nltk.download('{}')" < /app/nltk.txt

# Copy over files

COPY . /app

# Build and copy over assets

COPY --from=frontend /app/assets /app/assets

# Collect static files for Whitenoise

RUN python manage.py collectstatic --no-input --traceback
