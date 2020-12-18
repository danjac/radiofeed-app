web: gunicorn radiofeed.config.wsgi:application
release: python manage.py migrate --noinput
worker: celery -A radiofeed.config.celery_app worker -l INFO
