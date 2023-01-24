install: install-pip install-npm install-precommit install-nltk

install-pip:
	python -m pip install -r requirements-dev.txt

install-npm:
	npm ci

install-precommit:
	pre-commit install

install-nltk:
	xargs python -m nltk.downloader <./nltk.txt

update: update-pip update-npm update-precommit

update-pip: update-pip-default update-pip-dev

update-pip-default:
	pip-compile --upgrade pyproject.toml -o requirements.txt --resolver=backtracking --no-header --no-annotate

update-pip-dev:
	pip-compile --upgrade pyproject.toml --extra dev -o requirements-dev.txt --resolver=backtracking --no-header --no-annotate
	python -m pip install -r requirements-dev.txt

update-npm:
	npm run check-updates && npm install

update-precommit:
	pre-commit autoupdate

test:
	python -m pytest

db:
	python ./manage.py migrate
	python ./manage.py loaddata ./radiofeed/podcasts/fixtures/categories.json.gz
	python ./manage.py loaddata ./radiofeed/podcasts/fixtures/podcasts.json.gz


clean:
	git clean -Xdf
