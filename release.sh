#!/usr/bin/env bash

# migrations

./manage.py migrate

# clear cache

./manage.py clear_cache
