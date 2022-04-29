release: python manage.py migrate
web: gunicorn podtracker.wsgi
worker: python manage.py rqworker mail default feeds feeds:frequent feeds:sporadic
