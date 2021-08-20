all: build seed test run

build:
	docker-compose build

seed:
	./bin/manage seed_podcast_data

test:
	./bin/runtests -x

run:
	docker-compose up -d --remove-orphans --scale worker=4

