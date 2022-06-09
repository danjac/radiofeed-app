release: python manage.py migrate
web: gunicorn radiofeed.wsgi
worker: python manage.py rqworker default emails feeds
