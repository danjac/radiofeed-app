# create new pod
podman pod create --name audiopod -p 8000 -p 5432 -p 6379 -p 8025

# add new volume
mkdir -p ./db/audiotrails-volume

# build local images
buildah bud -f django.dockerfile -t danjac.dev/django.img .
buildah bud -f assets.dockerfile -t danjac.dev/assets.img .

# postgresql
podman run --name postgresql --pod audiopod -e POSTGRES_PASSWORD=postgres -d -v "./db/audiotrails-volume:/var/lib/postgresql/data:z" postgres:11.8

# redis
podman run --name redis --pod audiopod -d redis

# mailhog
podman run --name mailhog --pod audiopod -d mailhog/mailhog:v1.0.0

# webapp
podman run --name webapp --pod audiopod --env-file=.env -v ".:/app/:z" -d danjac.dev/django.img /start-django

# celeryworker
podman run --name celeryworker --pod audiopod --env-file=.env -v ".:/app/:z" -d danjac.dev/django.img /start-celeryworker

# celerybeat
podman run --name celerybeat --pod audiopod --env-file=.env -v ".:/app/:z" -d danjac.dev/django.img /start-celerybeat

# watch js
podman run --name watchjs --pod audiopod -v ".:/app/:z" -d danjac.dev/assets.img /start-watchjs

# watch css
podman run --name watchcss --pod audiopod -v ".:/app/:z" -d danjac.dev/assets.img /start-watchcss
