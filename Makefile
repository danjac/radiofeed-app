build:
	docker-compose -f local.yml build
	docker-compose -f local.yml build

up:
	docker-compose -f local.yml up -d --remove-orphans

down:
	docker-compose -f local.yml down --remove-orphans

restart:
	docker-compose -f local.yml restart

logs:
	docker-compose -f local.yml logs -f

