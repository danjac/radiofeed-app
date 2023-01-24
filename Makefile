build: install nltk

install:
	python -m pip install -r requirements-dev.txt
	npm ci
	pre-commit install

nltk:
	xargs python -m nltk.downloader <./nltk.txt

test:
	python -m pytest

db:
	python ./manage.py migrate
	python ./manage.py loaddata ./radiofeed/podcasts/fixtures/categories.json.gz
	python ./manage.py loaddata ./radiofeed/podcasts/fixtures/podcasts.json.gz

update: update-production update-development update-npm update-precommit

update-production:
	pip-compile --upgrade pyproject.toml -o requirements.txt --resolver=backtracking --no-header --no-annotate

update-development:
	pip-compile --upgrade pyproject.toml --extra dev -o requirements-dev.txt --resolver=backtracking --no-header --no-annotate
	python -m pip install -r requirements-dev.txt

update-npm:
	npm run check-updates && npm install

update-precommit:
	pre-commit autoupdate

clean:
	git clean -Xdf
