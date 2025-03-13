#!/usr/bin/env bash

set -o errexit

MANAGE="python ./manage.py"

# Run system checks
echo "Running system checks..."
$MANAGE check --deploy --traceback

# Run database migrations
echo "Running database migrations..."
$MANAGE migrate --no-input --traceback

# Clear cache
echo "Clearing cache..."
$MANAGE clear_cache --traceback
