#!/bin/bash

set -o errexit
set -o nounset

IMAGE=audiotrails:latest
POD=audiopod

echo "building image $IMAGE"
podman build -t $IMAGE .

if podman pod exists $POD
then
    echo "stopping and removing pod $POD"
    podman pod stop $POD
    podman pod rm $POD
fi

echo "creating new pod $POD"
podman pod create --name $POD -p 8000:8000 -p 8025:8025 -p 1025 -p 5432 -p 6379

echo "starting postgresql"
mkdir -p ${PWD}/db

podman run --name postgresql \
    --pod $POD \
    -e POSTGRES_PASSWORD=postgres \
    -d -v "${PWD}/db:/var/lib/postgresql/data:z" postgres:11.8

echo "starting redis"
podman run --name redis --pod $POD -d redis

echo "starting mailhog: runs test mail server on http://localhost:8025"
podman run --name mailhog --pod $POD -d mailhog/mailhog:v1.0.0

VOLUME="${PWD}:/app/:z"

echo "starting webapp: runs Django development server on http://localhost:8000"
podman run --name webapp \
    --pod $POD \
    --env-file=.env \
    -v $VOLUME \
    -d $IMAGE /start-django

echo "starting celeryworker: runs celery process"
podman run --name celeryworker \
    --pod $POD \
    --env-file=.env \
    -v $VOLUME \
    -d $IMAGE /start-celeryworker

echo "starting watchjs: runs esbuild process"
podman run --name watchjs \
    --pod $POD \
    --env-file=.env \
    -v $VOLUME \
    -d $IMAGE /start-watchjs

echo "starting watchcss: runs Tailwind JIT process"
podman run --name watchcss \
    --pod $POD \
    --env-file=.env \
    -v $VOLUME \
    -d $IMAGE /start-watchcss

echo "creating celerybeat: to start run 'podman start celerybeat'"
podman create --name celerybeat \
    --pod $POD \
    --env-file=.env \
    -v $VOLUME \
    $IMAGE /start-celerybeat
