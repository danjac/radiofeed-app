install:
	docker-compose build
	poetry install
	npm ci
