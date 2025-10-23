#!/usr/bin/env bash

set -o errexit

ssh -t "ubuntu@157.180.28.166" -- ./manage.sh "$@"
