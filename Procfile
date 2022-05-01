web: python manage.py migrate && gunicorn podtracker.wsgi
worker: python manage.py rqworker mail default feeds feeds:frequent feeds:sporadic
