release:
  npm install \
  && npm run build-css \
  && python manage.py collectstatic --noinput -v 3 -i css -i dev -i silk \
  && python manage.py migrate \
  && python manage.py clear_cache -a

web: gunicorn --workers=2 --max-requests=1000 --max-requests-jitter=50 audiotrails.config.wsgi
worker: celery -A audiotrails.config.celery_app worker -l INFO --concurrency=4
beat: celery -A audiotrails.celery_app beat -l INFO --scheduler django_celery_beat.schedulers:DatabaseScheduler

