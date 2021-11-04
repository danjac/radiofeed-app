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
	./bin/manage migrate

superuser:
	./bin/manage createsuperuser

seed:
	./bin/manage seed_podcast_data

parse:
	./bin/manage parse_podcast_feeds

reschedule:
	./bin/manage parse_podcast_feeds --reschedule

shell:
	./bin/manage shell_plus

test:
	./bin/runtests -v -x --ff --reuse-db

coverage:
	./bin/runtests -v -x --cov --reuse-db --cov-report term-missing

reqs: requirements

requirements:
	./bin/poetry export -o requirements.txt  --without-hashes

upgrade:
	./bin/poetry update -vv
	./bin/poetry export -o requirements.txt  --without-hashes
	./bin/npm update

maint: maintenance

maintenance:
	ansible-playbook maintenance.yml --ask-pass

push:
	git push dokku main
