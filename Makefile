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
	./local/bin/manage migrate

superuser:
	./local/bin/manage createsuperuser

seed:
	./local/bin/manage loaddata podcasts radiofeed/podcasts/fixtures/categories.json.gz
	./local/bin/manage loaddata podcasts radiofeed/podcasts/fixtures/podcasts.json.gz

shell:
	./local/bin/manage shell_plus

test:
	./local/bin/pytest

coverage:
	./local/bin/pytest -v -x --cov --reuse-db --cov-report term-missing

upgrade:
	pip-compile --upgrade requirements.in
	./local/bin/npm upgrade

requirements:
	pip-compile requirements.in
