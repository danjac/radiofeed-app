release: ./release.sh
web: gunicorn radiofeed.wsgi -w 8
worker: python manage.py rqworker emails feeds
