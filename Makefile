all: build migrate seed test run

build:
	docker-compose build

migrate:
	./bin/manage migrate

seed:
	./bin/manage seed_podcast_data

test:
	./bin/runtests -v -x --ff --reuse-db

coverage:
	./bin/runtests -v -x --cov --reuse-db

run:
	docker-compose up -d --remove-orphans --scale worker=4

