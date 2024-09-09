# Production Dockerfile for application
FROM node:22-bookworm-slim AS tailwind

WORKDIR /app

# Asset requirements

COPY package*.json /app/

RUN npm install

# Build assets

COPY tailwind.config.js /app/

COPY assets/tailwind.css /app/assets/

COPY templates/ /app/

ENV NODE_ENV=production

RUN npm run tailwind:build && rm -rf node_modules

# Install Python dependencies

FROM python:3.12.4-bookworm AS django

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

COPY ./pyproject.toml ./pdm.lock /app/

RUN pdm install --check --prod --no-editable --no-self --fail-fast

ENV PATH="/app/.venv/bin:$PATH"

# Download NLTK files

COPY ./nltk.txt /app/nltk.txt

RUN xargs -I{} python -c "import nltk; nltk.download('{}')" < /app/nltk.txt

COPY . /app

# Compile Tailwind CSS

COPY --from=tailwind /app/assets/app.css /app/assets/

# Collect static files, compress blocks, and re-collect for Whitenoise

RUN python manage.py collectstatic --no-input && \
    python manage.py compress --force && \
    python manage.py collectstatic --no-input
