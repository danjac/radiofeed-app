#!/usr/bin/env bash

set -o errexit

NUM_WORKERS=$(nproc --all)

granian radiofeed.wsgi:application \
    --host 0.0.0.0 \
    --port "${PORT:=8000}" \
    --workers "${NUM_WORKERS}" \
    --interface wsgi
