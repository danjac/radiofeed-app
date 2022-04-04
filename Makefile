all: build start migrate test seed

build:
	docker-compose build

start:
	docker-compose up -d --remove-orphans

stop:
	docker-compose down

restart:
	docker-compose restart

logs:
	docker-compose logs -f

migrate:
	./scripts/manage migrate

superuser:
	./scripts/manage createsuperuser

seed:
	./scripts/manage seed_podcast_data

shell:
	./scripts/manage shell_plus

test:
	./scripts/pytest -v -x --ff --reuse-db

coverage:
	./scripts/pytest -v -x --cov --reuse-db --cov-report term-missing

requirements:
	pip-compile requirements.in

upgrade:
	pip-compile --upgrade requirements.in
	./scripts/npm upgrade
