web: python manage.py migrate && gunicorn 0.0.0.0:8000 radiofeed.wsgi
worker: python manage.py run_huey -w 2
