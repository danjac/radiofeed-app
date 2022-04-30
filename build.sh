#!/usr/bin/env bash
# exit on error
set -o errexit

pip install -r requirements.txt

xargs python -m nltk.downloader <./nltk.txt

python manage.py collectstatic --no-input
python manage.py migrate
