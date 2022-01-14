all: build start migrate test seed

build:
	docker-compose build

start:
	docker-compose up -d --remove-orphans --scale worker=4

stop:
	docker-compose down

restart:
	docker-compose restart

logs:
	docker-compose logs -f

migrate:
	./bin/manage migrate

superuser:
	./bin/manage createsuperuser

seed:
	./bin/manage seed_podcast_data

shell:
	./bin/manage shell_plus

test:
	./bin/runtests -v -x --ff --reuse-db

coverage:
	./bin/runtests -v -x --cov --reuse-db --cov-report term-missing

reqs: requirements

requirements:
	pip-compile requirements.in
	pip-compile dev-requirements.in

upgrade:
	pip-compile --upgrade requirements.in
	pip-compile --upgrade dev-requirements.in

maint: maintenance

maintenance:
	ansible-playbook maintenance.yml --ask-pass


push:
	git push dokku main
