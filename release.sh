#!/usr/bin/env bash

# migrations

./manage.py migrate

# update translations

./manage.py update_translation_fields
