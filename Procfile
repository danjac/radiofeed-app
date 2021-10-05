web: gunicorn --workers=2 --max-requests=1000 --max-requests-jitter=50 jcasts.config.wsgi
worker: python manage.py rqworker --with-scheduler mail default feeds
