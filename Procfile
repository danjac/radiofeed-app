release: ./release.sh
web: gunicorn -c ./gunicorn.conf.py
feedparser: python ./manage.py parse_feeds --watch
subscriber: python ./manage.py subscribe_websub_feeds --watch
