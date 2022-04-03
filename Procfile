web: gunicorn --workers=5 --max-requests=1000 --max-requests-jitter=50 jcasts.wsgi
worker: python manage.py rqworker mail default feeds feeds:frequent feeds:sporadic
