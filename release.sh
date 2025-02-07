#!/usr/bin/env bash

set -o errexit

MANAGE="python ./manage.py"

# Run system checks
$MANAGE check --deploy --traceback

# Run database migrations
$MANAGE migrate --no-input --traceback

# Run health checks
$MANAGE health_check --traceback

# Clear cache
$MANAGE clear_cache --traceback
