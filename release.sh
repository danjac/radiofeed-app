#!/usr/bin/env bash

set -o errexit

# commands run on new deployment:
# 1. security and other checks
# 2. database migrations
# 3. system health checks
# 4. clear cache


python ./manage.py check --deploy --traceback

# increase statement timeout for larger migrations
STATEMENT_TIMEOUT=300 python ./manage.py migrate --no-input --traceback

python ./manage.py health_check --traceback

python ./manage.py clear_cache --traceback
