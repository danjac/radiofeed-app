all: build migrate seed test run

build:
	docker-compose build

migrate:
	./bin/manage migrate

seed:
	./bin/manage seed_podcast_data

test:
	./bin/runtests -x

run:
	docker-compose up -d --remove-orphans --scale worker=4

