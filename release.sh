#!/usr/bin/env bash

set -o errexit

# increase statement timeout for larger migrations
export STATEMENT_TIMEOUT=300

python ./manage.py check --deploy

python ./manage.py migrate --no-input

python ./manage.py health_check

python ./manage.py clear_cache
