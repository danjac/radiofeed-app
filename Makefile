install: poetryinstall npminstall precommitinstall nltkdownload

dbinstall: migrate fixtures

update: poetryupdate npmupdate precommitupdate

poetryinstall:
	poetry install --no-root --no-cache -vvv

poetryupdate:
	poetry update --no-cache -vvv

poetryexport:
	poetry export -o requirements.txt --without-hashes -vvvv
	poetry export -o requirements-ci.txt --with=dev --without-hashes -vvvv

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
