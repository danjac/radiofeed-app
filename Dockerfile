# Production Dockerfile for application

FROM node:20-bookworm-slim AS assets

WORKDIR /app

# Asset requirements

COPY ./package.json /app/package.json

COPY ./package-lock.json /app/package-lock.json

RUN npm install

# Build assets

COPY . /app

ENV NODE_ENV=production

RUN npm run build

FROM python:3.12-bullseye AS app

ENV PYTHONUNBUFFERED=1

ENV PYTHONDONTWRITEBYTECODE=1

ENV PIP_DISABLE_PIP_VERSION_CHECK=1

ENV PIP_ROOT_USER_ACTION=ignore

WORKDIR /app

# Python requirements

COPY ./requirements.txt /app/requirements.txt

RUN pip install -r /app/requirements.txt --no-cache-dir

# Download NLTK files

COPY ./nltk.txt /app/nltk.txt

RUN xargs -I{} python -c "import nltk; nltk.download('{}')" < /app/nltk.txt

# Copy over files

COPY . /app

# Build and copy over assets

COPY --from=assets /app/static /app/static

# Collect static files for Whitenoise

RUN python manage.py collectstatic --no-input --traceback
