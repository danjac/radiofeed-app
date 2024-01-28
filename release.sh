#!/usr/bin/env bash

set -o errexit

./manage.py check --deploy

./manage.py health_check

./manage.py migrate

./manage.py clear_cache
