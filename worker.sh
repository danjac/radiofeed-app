#!/usr/bin/env bash

set -o errexit

exec python ./manage.py db_worker
