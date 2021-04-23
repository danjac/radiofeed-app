#!/bin/bash

set -o errexit
set -o nounset

podman pod create --name audiopod -p 8000:8000 -p 5432 -p 6379 -p 8025

mkdir -p ${PWD}/db

podman run --name postgresql --pod audiopod -e POSTGRES_PASSWORD=postgres -d -v "${PWD}/db:/var/lib/postgresql/data:z" postgres:11.8

# redis
podman run --name redis --pod audiopod -d redis

# mailhog
podman run --name mailhog --pod audiopod -d mailhog/mailhog:v1.0.0

# webapp
podman run --name webapp \
    --pod audiopod \
    --env-file=.env \
    -v "${PWD}:/app/:z" \
    -d danjac.dev/django /start-django

# celeryworker
podman run --name celeryworker \
    --pod audiopod \
    --env-file=.env \
    -v "${PWD}:/app/:z" \
    -d danjac.dev/django /start-celeryworker

# celerybeat
podman run --name celerybeat \
    --pod audiopod \
    --env-file=.env \
    -v "${PWD}:/app/:z" \
    -d danjac.dev/django /start-celerybeat

# watch js
podman run --name watchjs \
    --pod audiopod \
    -v "${PWD}:/app/:z" \
    -d danjac.dev/assets /start-watchjs

# watch css
podman run --name watchcss \
    --pod audiopod \
    -v "${PWD}:/app/:z" \
    -d danjac.dev/assets /start-watchcss
