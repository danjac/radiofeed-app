install: pipinstall npminstall precommitinstall nltkdownload

dbinstall: migrate fixtures

update: pipupdate npmupdate precommitupdate

pipinstall:
	pip install -r requirements-dev.txt

pipupdate:
	pip-compile pyproject.toml -o requirements.txt --resolver=backtracking --no-header --no-annotate --upgrade
	pip-compile pyproject.toml -o requirements-dev.txt --extra=dev --resolver=backtracking --no-header --no-annotate --upgrade
	pip install -r requirements-dev.txt

npminstall:
	npm ci

npmupdate:
	npm run check-updates && npm install

precommitinstall:
	pre-commit install

precommitupdate:
	pre-commit autoupdate

nltkdownload:
	cat nltk.txt | xargs -I{} python -c "import nltk; nltk.download('{}')"

migrate:
	python ./manage.py migrate

fixtures:
	python ./manage.py loaddata ./radiofeed/podcasts/fixtures/categories.json.gz
	python ./manage.py loaddata ./radiofeed/podcasts/fixtures/podcasts.json.gz
	python ./manage.py loaddata ./radiofeed/users/fixtures/users.json.gz

serve:
	python ./manage.py runserver

shell:
	python ./manage.py shell_plus

build:
	npm run build

watch:
	npm run watch

test:
	python -m pytest

clean:
	git clean -Xdf
