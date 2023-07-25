# Production Dockerfile for application

FROM node:20-buster AS assets

WORKDIR /app

# Asset requirements

COPY ./package.json /app/package.json

COPY ./package-lock.json /app/package-lock.json

RUN npm install

# Asset files

COPY ./static/css /app/static/css

COPY ./static/js /app/static/js

COPY ./tailwind.config.js /app/tailwind.config.js

# Tailwind requires access to Django templates

COPY ./templates /app/templates

# Build assets

ENV NODE_ENV=production

RUN npm run build

FROM python:3.11.4-buster AS app

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

RUN xargs -I{} python -c "import nltk; nltk.download('{}')" < nltk.txt

# Copy all app files

COPY . /app

# Build and copy over assets

COPY --from=assets /app/static /app/static

# Collect static files for Whitenoise

RUN python manage.py collectstatic --no-input --traceback
