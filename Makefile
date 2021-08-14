build:
	docker-compose build

install:
	./bin/manage seed_podcast_data

run:
	docker-compose up -d --remove-orphans --scale worker=4

