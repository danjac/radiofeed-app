web: gunicorn --workers=2 --max-requests=1000 --max-requests-jitter=50 jcasts.config.wsgi
worker: python manage.py rqworker mail default feeds
podping: python manage.py podping --from-minutes-ago=15 --keep-alive
