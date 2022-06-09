release: python manage.py migrate
web: gunicorn radiofeed.wsgi -w 3
worker: python manage.py rqworker default emails feeds
