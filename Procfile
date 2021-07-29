# release: python manage.py clear_cache -a
web: gunicorn --workers=2 --max-requests=1000 --max-requests-jitter=50 jcasts.config.wsgi
worker: python manage.py rqworker default feeds mail
