compose:
	docker-compose up -d

install:
	npm ci
	poetry install
	xargs python -m nltk.downloader <./nltk.txt

db:
	python manage.py migrate
	python manage.py loaddata ./radiofeed/podcasts/fixtures/categories.json.gz
	python manage.py loaddata ./radiofeed/podcasts/fixtures/podcasts.json.gz

test:
	python -m pytest

start:
	python -m honcho start -f honcho.procfile

upgrade:
	poetry update
	npm run check-updates && npm install
	pre-commit autoupdate
