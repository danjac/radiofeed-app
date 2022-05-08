build:
	docker-compose -f local.yml build

up:
	docker-compose -f local.yml up -d --remove-orphans

down:
	docker-compose -f local.yml down --remove-orphans

restart:
	docker-compose -f local.yml restart

logs:
	docker-compose -f local.yml logs -f

migrate:
	./bin/manage migrate

superuser:
	./bin/manage createsuperuser

seed:
	./bin/manage loaddata podcasts radiofeed/podcasts/fixtures/categories.json.gz
	./bin/manage loaddata podcasts radiofeed/podcasts/fixtures/podcasts.json.gz

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
