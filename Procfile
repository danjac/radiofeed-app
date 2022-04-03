release: python manage.py migrate
web: gunicorn --preload jcasts.wsgi
worker: python manage.py rqworker mail default feeds feeds:frequent feeds:sporadic
