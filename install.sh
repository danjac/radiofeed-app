#!/bin/bash

set -o errexit
set -o nounset

IMAGE=audiotrails:latest

podman build -t $IMAGE .

podman pod create --name audiopod -p 8000:8000 -p 8025:8025 -p 1025 -p 5432 -p 6379

# postgres
mkdir -p ${PWD}/db

podman run --name postgresql \
    --pod audiopod \
    -e POSTGRES_PASSWORD=postgres \
    -d -v "${PWD}/db:/var/lib/postgresql/data:z" postgres:11.8

# redis
podman run --name redis --pod audiopod -d redis

# mailhog
podman run --name mailhog --pod audiopod -d mailhog/mailhog:v1.0.0

# webapp
podman run --name webapp \
    --pod audiopod \
    --env-file=.env \
    -v "${PWD}:/app/:z" \
    -d $IMAGE /start-django

# celeryworker
podman run --name celeryworker \
    --pod audiopod \
    --env-file=.env \
    -v "${PWD}:/app/:z" \
    -d $IMAGE /start-celeryworker

# celerybeat
podman run --name celerybeat \
    --pod audiopod \
    --env-file=.env \
    -v "${PWD}:/app/:z" \
    -d $IMAGE /start-celerybeat

# watch js
podman run --name watchjs \
    --pod audiopod \
    --env-file=.env \
    -v "${PWD}:/app/:z" \
    -d $IMAGE /start-watchjs

# watch css
podman run --name watchcss \
    --pod audiopod \
    --env-file=.env \
    -v "${PWD}:/app/:z" \
    -d $IMAGE /start-watchcss
