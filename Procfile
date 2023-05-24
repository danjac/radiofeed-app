release: ./release.sh
web: gunicorn -c ./gunicorn.conf.py
worker: python manage.py rqworker high default low
