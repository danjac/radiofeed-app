build: install nltk

compose:
	docker-compose up -d

install:
	pip install -r dev-requirements.txt
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
	pip-compile --upgrade pyproject.toml --extra prod -o requirements.txt
	pip-compile --upgrade pyproject.toml --extra ci -o ci-requirements.txt
	pip-compile --upgrade pyproject.toml --extra dev -o dev-requirements.txt
	npm run check-updates && npm install
	pre-commit autoupdate
