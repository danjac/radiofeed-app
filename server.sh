#!/usr/bin/env bash

set -o errexit

exec python -m gunicorn -c ./gunicorn.conf.py -b "0.0.0.0:${PORT:=8000}"
