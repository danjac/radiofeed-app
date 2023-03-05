#!/usr/bin/env bash

set -o errexit

./manage.py check --deploy

./manage.py migrate

./manage.py clear_cache
