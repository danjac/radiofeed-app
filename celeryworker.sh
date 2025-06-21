#!/usr/bin/env bash

set -o errexit

python -m celery -A radiofeed worker --loglevel INFO
