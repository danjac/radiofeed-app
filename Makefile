build: install nltk

compose:
	docker-compose up -d

install:
	npm ci
	poetry install
	pre-commit install

nltk:
	xargs poetry run nltk.downloader <./nltk.txt

db:
	poetry run ./manage.py migrate
	poetry run ./manage.py loaddata ./radiofeed/podcasts/fixtures/categories.json.gz
	poetry run ./manage.py loaddata ./radiofeed/podcasts/fixtures/podcasts.json.gz

test:
	poetry run pytest

start:
	poetry run honcho start -f honcho.procfile

clean:
	git clean -Xdf

upgrade:
	poetry update
	npm run check-updates && npm install
	pre-commit autoupdate
