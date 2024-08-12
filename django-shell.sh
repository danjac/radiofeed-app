#!/usr/bin/env bash

set -o errexit

DJANGO_READ_ONLY=1 python manage.py shell_plus
