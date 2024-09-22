#!/usr/bin/env bash

set -o errexit

# commands run on new deployment:
# 1. security and other checks
# 2. database migrations
# 3. system health checks
# 4. clear cache

python ./manage.py check --deploy --traceback

python ./manage.py migrate --no-input --traceback

python ./manage.py health_check --traceback

python ./manage.py clear_cache --traceback
