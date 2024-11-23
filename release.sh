#!/usr/bin/env bash

set -o errexit

# commands run on new deployment:
# 1. security and other checks
# 2. database migrations
# 3. system health checks
# 4. clear cache
#

MANAGE="python ./manage.py"

$MANAGE check --deploy --traceback

$MANAGE migrate --no-input --traceback

$MANAGE health_check --traceback

$MANAGE clear_cache --traceback
