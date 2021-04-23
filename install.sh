#!/bin/bash

set -o errexit
set -o nounset

IMAGE=audiotrails:latest
POD=audiopod

podman build -t $IMAGE .

if podman pod exists $POD
then
    podman pod stop $POD
    podman pod rm $POD
fi

podman pod create --name $POD -p 8000:8000 -p 8025:8025 -p 1025 -p 5432 -p 6379

# postgres
mkdir -p ${PWD}/db

podman run --name postgresql \
    --pod $POD \
    -e POSTGRES_PASSWORD=postgres \
    -d -v "${PWD}/db:/var/lib/postgresql/data:z" postgres:11.8

# redis
podman run --name redis --pod $POD -d redis

# mailhog
podman run --name mailhog --pod $POD -d mailhog/mailhog:v1.0.0

# webapp
podman run --name webapp \
    --pod $POD \
    --env-file=.env \
    -v "${PWD}:/app/:z" \
    -d $IMAGE /start-django

# celeryworker
podman run --name celeryworker \
    --pod $POD \
    --env-file=.env \
    -v "${PWD}:/app/:z" \
    -d $IMAGE /start-celeryworker

# celerybeat
podman run --name celerybeat \
    --pod $POD \
    --env-file=.env \
    -v "${PWD}:/app/:z" \
    -d $IMAGE /start-celerybeat

# watch js
podman run --name watchjs \
    --pod $POD \
    --env-file=.env \
    -v "${PWD}:/app/:z" \
    -d $IMAGE /start-watchjs

# watch css
podman run --name watchcss \
    --pod $POD \
    --env-file=.env \
    -v "${PWD}:/app/:z" \
    -d $IMAGE /start-watchcss
