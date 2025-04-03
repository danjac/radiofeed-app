#!/usr/bin/env bash

set -o errexit

# Runs Django management commands to prepare the application for release:
# - checks the deployment settings
# - runs health checks
# - applies database migrations
# - clear cache

MANAGE="python ./manage.py"

$MANAGE check --deploy --traceback
$MANAGE migrate --no-input --traceback
$MANAGE clear_cache --traceback
$MANAGE health_check --traceback
