#!/usr/bin/env bash

set -o errexit

# Starts the scheduler worker.

MANAGE="python ./manage.py"

$MANAGE qcluster
