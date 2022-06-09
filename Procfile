release: python manage.py migrate
web: gunicorn radiofeed.wsgi -w $(( 2 * `cat /proc/cpuinfo | grep 'core id' | wc -l` + 1 ))
worker: python manage.py rqworker default emails feeds
