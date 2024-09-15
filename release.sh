#!/usr/bin/env bash

set -o errexit

# increase statement timeout for larger migrations
export STATEMENT_TIMEOUT=300

python ./manage.py check --deploy --traceback

python ./manage.py migrate --no-input --traceback

python ./manage.py health_check --traceback

python ./manage.py clear_cache --traceback
