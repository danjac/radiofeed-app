#!/usr/bin/env bash

# check all secure

./manage.py check --deploy

# migrations

./manage.py migrate

# clear cache

./manage.py clear_cache

# start pgbouncer

bin/start-pgbouncer

# start server

gunicorn -c ./gunicorn.conf.py radiofeed.wsgi --access-logfile -
