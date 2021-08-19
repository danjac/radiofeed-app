build:
	docker-compose build

install:
	./bin/manage seed_podcast_data

test:
	./bin/runtests -x

run:
	docker-compose up -d --remove-orphans --scale worker=4

