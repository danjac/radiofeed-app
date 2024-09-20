#!/usr/bin/env bash

set -o errexit

# compile and deploy static assets
#
python manage.py tailwind build

python manage.py collectstatic --no-input
