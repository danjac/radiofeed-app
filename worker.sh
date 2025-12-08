#!/usr/bin/env bash

set -o errexit

python ./manage.py db_worker
