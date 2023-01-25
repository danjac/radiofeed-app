install: install-pip install-npm install-precommit install-nltk

update: update-pip install-pip update-npm update-precommit

install-pip:
	pip install -r requirements-dev.txt

install-npm:
	npm ci

install-precommit:
	pre-commit install

install-nltk:
	xargs python -m nltk.downloader <./nltk.txt

update-pip:
	pip-compile --upgrade pyproject.toml -o requirements.txt --no-header --no-annotate --resolver=backtracking
	pip-compile --upgrade pyproject.toml --extra dev -o requirements-dev.txt --no-header --no-annotate --resolver=backtracking

update-npm:
	npm run check-updates && npm install

update-precommit:
	pre-commit autoupdate

test:
	python -m pytest

shell:
	python ./manage.py shell_plus

serve:
	python ./manage.py runserver

watch:
	npm run watch

db:
	python ./manage.py migrate
	python ./manage.py loaddata ./radiofeed/podcasts/fixtures/categories.json.gz
	python ./manage.py loaddata ./radiofeed/podcasts/fixtures/podcasts.json.gz

clean:
	git clean -Xdf
