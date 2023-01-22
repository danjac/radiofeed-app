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

clean:
	git clean -Xdf

update:
	poetry update
	npm run check-updates && npm install
	pre-commit autoupdate
