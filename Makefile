build:
	docker-compose build

up:
	docker-compose up -d --remove-orphans --scale worker=2

down:
	docker-compose down --remove-orphans

restart:
	docker-compose restart

logs:
	docker-compose logs -f

migrate:
	./bin/manage migrate

schedule:
	./bin/manage schedule_podcast_feeds --primary && ./bin/manage schedule_podcast_feeds

superuser:
	./bin/manage createsuperuser

seed:
	./bin/manage seed_podcast_data

shell:
	./bin/manage shell_plus

test:
	./bin/pytest

coverage:
	./bin/pytest -v -x --cov --reuse-db --cov-report term-missing

upgrade:
	pip-compile --upgrade requirements.in
	./bin/npm upgrade

requirements:
	pip-compile requirements.in
