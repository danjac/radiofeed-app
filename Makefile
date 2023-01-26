install: install-poetry install-npm install-precommit install-nltk

update: update-poetry update-npm update-precommit

install-poetry:
	poetry install --no-root -vvv

install-npm:
	npm ci

install-precommit:
	pre-commit install

install-nltk:
	xargs python -m nltk.downloader <./nltk.txt

update-poetry:
	poetry update --no-cache -vvv

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
