install: poetryinstall npminstall precommitinstall nltkdownload

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

test:
	python -m pytest

shell:
	python ./manage.py shell_plus

serve:
	python ./manage.py runserver

db:
	python ./manage.py migrate
	python ./manage.py loaddata ./radiofeed/podcasts/fixtures/categories.json.gz
	python ./manage.py loaddata ./radiofeed/podcasts/fixtures/podcasts.json.gz

watch:
	npm run watch

clean:
	git clean -Xdf
