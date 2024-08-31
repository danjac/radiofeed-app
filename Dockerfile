# Production Dockerfile for application

FROM node:22-bookworm-slim AS frontend

WORKDIR /app

# Asset requirements

COPY package*.json ./

RUN npm install

# Build assets

COPY . /app

ENV NODE_ENV=production

RUN npm run build && rm -rf node_modules

# Python

FROM python:3.12.4-bookworm AS backend

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

# Download NLTK files

COPY ./nltk.txt /app/nltk.txt

RUN pdm run xargs -I{} python -c "import nltk; nltk.download('{}')" < /app/nltk.txt

# Copy over files

COPY . /app

# Build and copy over assets

COPY --from=frontend /app/assets /app/assets

# Collect static files for Whitenoise

RUN pdm run python manage.py collectstatic --no-input --traceback
