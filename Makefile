all: build start migrate test seed

build:
	docker-compose build

start:
	docker-compose up -d --remove-orphans --scale worker=2

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

dokku-shell:
	./scripts/dokku-manage shell_plus

test:
	./scripts/runtests -v -x --ff --reuse-db

coverage:
	./scripts/runtests -v -x --cov --reuse-db --cov-report term-missing

reqs: requirements

requirements:
	pip-compile requirements.in

upgrade:
	pip-compile --upgrade requirements.in
	ncu -u
	npm install


maint: maintenance

maintenance:
	ansible-playbook maintenance.yml --ask-pass


push:
	git push dokku main
