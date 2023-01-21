#!/usr/bin/env bash

# check secure

./manage.py check --deploy

# migrations

./manage.py migrate

# clear cache

./manage.py clear_cache

# static files

./manage.py collectstatic --no-input --clear

# start server

gunicorn -c ./gunicorn.conf.py radiofeed.wsgi
