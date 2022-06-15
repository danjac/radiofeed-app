release: python manage.py migrate
web: gunicorn radiofeed.wsgi -w 4
worker: REMAP_SIGTERM=SIGQUIT celery -A radiofeed.celery_app worker --loglevel=info
