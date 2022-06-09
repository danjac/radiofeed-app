release: python manage.py migrate
web: gunicorn radiofeed.wsgi -w 4
worker: python manage.py rqworker default emails feeds
