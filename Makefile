build:
	docker-compose build

up:
	docker-compose up -d --remove-orphans

down:
	docker-compose down --remove-orphans

restart:
	docker-compose restart

logs:
	docker-compose logs -f

