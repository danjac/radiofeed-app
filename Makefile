build: install nltk

compose:
	docker-compose up -d

install:
	python -m pip install -r requirements.txt
	npm ci
	pre-commit install

nltk:
	xargs python -m nltk.downloader <./nltk.txt

db:
	python ./manage.py migrate
	python ./manage.py loaddata ./radiofeed/podcasts/fixtures/categories.json.gz
	python ./manage.py loaddata ./radiofeed/podcasts/fixtures/podcasts.json.gz

clean:
	git clean -Xdf

update:
	pip-compile requirements.in -o requirements.txt --resolver=backtracking
	python -m pip install -r requirements-dev.txt
	npm run check-updates && npm install
	pre-commit autoupdate
