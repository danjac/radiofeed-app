build: install nltk

compose:
	docker-compose up -d

install:
	python -m pip install -r requirements-dev.txt
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
	pip-compile requirements/base.in requirements/prod.in -o requirements.txt --resolver=backtracking
	pip-compile requirements/base.in requirements/ci.in -o requirements-ci.txt --resolver=backtracking
	pip-compile requirements/base.in requirements/dev.in -o requirements-ci.txt --resolver=backtracking
	python -m pip install -r requirements-dev.txt
	npm run check-updates && npm install
	pre-commit autoupdate
