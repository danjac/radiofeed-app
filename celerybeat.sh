#!/usr/bin/env bash

set -o errexit

python -m celery -A radiofeed beat \
    --loglevel INFO \
    --scheduler django_celery_beat.schedulers:DatabaseScheduler
