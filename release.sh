#!/usr/bin/env bash

set -o errexit

# Runs Django management commands to prepare the application for release:
# - checks the deployment settings
# - applies database migrations
# - runs health checks

MANAGE="python ./manage.py"

$MANAGE check --deploy --traceback
$MANAGE migrate --no-input --traceback
$MANAGE health_check --traceback
