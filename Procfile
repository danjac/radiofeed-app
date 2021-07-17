release: python manage.py clear_cache -a
web: gunicorn --workers=2 --max-requests=1000 --max-requests-jitter=50 jcasts.config.wsgi
worker: celery -A jcasts.config.celery_app worker -l INFO --concurrency=4
beat: celery -A jcasts.celery_app beat -l INFO --scheduler django_celery_beat.schedulers:DatabaseScheduler

