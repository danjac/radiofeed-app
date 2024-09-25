#!/usr/bin/env bash

set -o errexit

granian radiofeed.wsgi:application \
    --host 0.0.0.0 \
    --port "${PORT:=8000}" \
    --workers "$(nproc --all)" \
    --interface wsgi
