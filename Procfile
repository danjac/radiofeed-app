release: python manage.py migrate && python manage.py clear_cache -a
web: gunicorn --workers=2 --max-requests=1000 --max-requests-jitter=50 radiofeed.config.asgi -k uvicorn.workers.UvicornWorker
worker: celery -A radiofeed.config.celery_app worker -l INFO
beat: celery -A radiofeed.celery_app beat -l INFO --scheduler django_celery_beat.schedulers:DatabaseScheduler
