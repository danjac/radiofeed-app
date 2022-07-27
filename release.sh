#!/usr/bin/env bash

# migrations

./manage.py migrate

# clear cache

./manage.py clear_cache

# update translations

./manage.py update_translation_fields
