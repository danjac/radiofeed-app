release: ./release.sh
web: gunicorn -c ./gunicorn.conf.py
feedparser: python ./manage.py parse_feeds --watch --limit=720
