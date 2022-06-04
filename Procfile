release: python manage.py migrate
web: gunicorn radiofeed.wsgi
worker: celery -A radiofeed.celery_app worker -l INFO
scheduler: celery -A radiofeed.celery_app beat -l INFO
