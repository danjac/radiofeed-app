install: pyinstall npminstall precommitinstall nltkdownload

dbinstall: migrate fixtures

update: pyupdate npmupdate precommitupdate

pyinstall:
	uv venv && source .venv/bin/activate
	uv pip install -r requirements-ci.txt

pydeps:
	uv pip compile pyproject.toml --upgrade -o requirements.txt
	uv pip compile pyproject.toml --upgrade --extra dev -o requirements-ci.txt

pysync:
	uv pip sync requirements-ci.txt

pyupdate: pydeps pysync

npminstall:
	npm ci

npmupdate:
	npm run check-updates && npm install

precommitinstall:
	pre-commit install

precommitupdate:
	pre-commit autoupdate

nltkdownload:
	xargs -I{} .venv/bin/python -c "import nltk; nltk.download('{}')" < nltk.txt

build:
	npm run build

watch:
	npm run watch

clean:
	git clean -Xdf

podbuild:
	podman play kube podman-kube.yml

podstart:
	podman pod start radiofeed-pod

podstop:
	podman pod stop radiofeed-pod

podclean:
	podman pod rm radiofeed-pod
	podman volume rm radiofeed_pg_data

test:
	python -m pytest

serve:
	python ./manage.py runserver

shell:
	python ./manage.py shell_plus

parsefeeds:
	python ./manage.py parse_feeds

droptestdb:
	python ./manage.py drop_test_database --no-input

clearcache:
	python ./manage.py clear_cache

migrate:
	python ./manage.py migrate

fixtures:
	python ./manage.py loaddata ./radiofeed/podcasts/fixtures/categories.json.gz
	python ./manage.py loaddata ./radiofeed/podcasts/fixtures/podcasts.json.gz
	python ./manage.py loaddata ./radiofeed/users/fixtures/users.json.gz
