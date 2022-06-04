release: python manage.py migrate
web: gunicorn radiofeed.config.wsgi
worker: celery -A radiofeed.config.celery_app worker -l INFO
scheduler: celery -A radiofeed.config.celery_app beat -l INFO
