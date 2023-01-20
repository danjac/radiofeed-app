#!/usr/bin/env bash

# check secure

./manage.py check --deploy

# staticfiles

./manage.py collectstatic

# migrations

./manage.py migrate

# clear cache

./manage.py clear_cache

# run gunicorn
gunicorn -c ./gunicorn.conf.py radiofeed.wsgi
