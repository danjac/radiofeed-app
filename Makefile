build:
	docker-compose build

up:
	docker-compose up -d --remove-orphans

down:
	docker-compose down --remove-orphans

restart:
	docker-compose restart

logs:
	docker-compose logs -f

migrate:
	./bin/manage migrate

superuser:
	./bin/manage createsuperuser

seed:
	./bin/manage loaddata podcasts podtracker/podcasts/fixtures/categories.json.gz
	./bin/manage loaddata podcasts podtracker/podcasts/fixtures/podcasts.json.gz

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
