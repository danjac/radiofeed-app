#!/bin/bash

set -o errexit
set -o nounset

podman pod create --name audiopod -p 8000 -p 5432 -p 6379 -p 8025

# create volume
podman volume create audiotrails
mntPoint=$(podman volume inspect audiotrails --format {{.Mountpoint}})

# postgres
dataDir=${mntPoint}/db
mkdir -p ${dataDir}

# media dirs
mediaDir=${mntPoint}/media
mkdir -p ${mediaDir}

# static dirs
staticDevDir=${mntPoint}/static/dev
mkdir -p ${staticDevDir}

staticDistDir=${mntPoint}/static/dist
mkdir -p ${staticDistDir}

# build local images
buildah bud -f django.dockerfile -t audiotrails.dev/django .
buildah bud -f assets.dockerfile -t audiotrails.dev/assets .

podman run --name postgresql --pod audiopod -e POSTGRES_PASSWORD=postgres -d -v "${dataDir}:/var/lib/postgresql/data:z" postgres:11.8

# redis
podman run --name redis --pod audiopod -d redis

# mailhog
podman run --name mailhog --pod audiopod -d mailhog/mailhog:v1.0.0

# webapp
podman run --name webapp \
    --pod audiopod \
    --env-file=.env \
    -v "${PWD}:/app/:z" \
    -v "${mediaDir}:/app/media:z" \
    -v "${staticDevDir}:/app/static/dev:z" \
    -v "${staticDistDir}:/app/static/dist:z" \
    -d audiotrails.dev/django /start-django

# celeryworker
podman run --name celeryworker \
    --pod audiopod \
    --env-file=.env \
    -v "${PWD}:/app/:z" \
    -v "${mediaDir}:/app/media:z" \
    -v "${staticDevDir}:/app/static/dev:z" \
    -v "${staticDistDir}:/app/static/dist:z" \
    -d audiotrails.dev/django /start-celeryworker

# celerybeat
podman run --name celerybeat \
    --pod audiopod \
    --env-file=.env \
    -v "${PWD}:/app/:z" \
    -v "${mediaDir}:/app/media:z" \
    -v "${staticDevDir}:/app/static/dev:z" \
    -v "${staticDistDir}:/app/static/dist:z" \
    -d audiotrails.dev/django /start-celerybeat

# watch js
podman run --name watchjs \
    --pod audiopod \
    -v "${PWD}:/app/:z" \
    -v "${staticDevDir}:/app/static/dev:z" \
    -v "${staticDistDir}:/app/static/dist:z" \
    -d audiotrails.dev/assets /start-watchjs

# watch css
podman run --name watchcss \
    --pod audiopod \
    -v "${PWD}:/app/:z" \
    -v "${staticDevDir}:/app/static/dev:z" \
    -v "${staticDistDir}:/app/static/dist:z" \
    -d audiotrails.dev/assets /start-watchcss
