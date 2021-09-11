all: build migrate seed test run

build:
	docker-compose build

run:
	docker-compose up -d --remove-orphans --scale worker=4

migrate:
	./bin/manage migrate

seed:
	./bin/manage seed_podcast_data

shell:
	./bin/manage shell_plus

test:
	./bin/runtests -v -x --ff --reuse-db --tb=no

coverage:
	./bin/runtests -v -x --cov --reuse-db --tb=no

upgrade:
	./bin/poetry update -vv
	./bin/poetry export -o requirements.txt  --without-hashes
	./bin/npm update

maint: maintenance

maintenance:
	ansible-playbook maintenance.yml --ask-pass

push:
	git push dokku main
