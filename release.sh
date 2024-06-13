#!/usr/bin/env bash

set -o errexit

python ./manage.py check --deploy

python ./manage.py migrate

python ./manage.py health_check

python ./manage.py clear_cache

python -m gunicorn -c ./gunicorn.conf.py
