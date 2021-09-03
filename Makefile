all: build migrate seed test run

build:
	docker-compose build

migrate:
	./bin/manage migrate

seed:
	./bin/manage seed_podcast_data

test:
	./bin/runtests -x --ff

coverage:
	./bin/runtests -x --cov

run:
	docker-compose up -d --remove-orphans --scale worker=4

