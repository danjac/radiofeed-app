  web: gunicorn -b --workers=1 --max-requests=1000 --max-requests-jitter=50 radiofeed.config.wsgi
  worker: celery -A radiofeed.config.celery_app worker -l INFO
