install:
	docker-compose build
	poetry install
	npm ci
	xargs python -m nltk.downloader <./nltk.txt

db:
	python manage.py migrate
	python manage.py loaddata ./radiofeed/podcasts/fixtures/categories.json.gz
	python manage.py loaddata ./radiofeed/podcasts/fixtures/podcasts.json.gz
