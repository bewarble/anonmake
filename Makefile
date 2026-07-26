.PHONY: docker-config docker-build docker-up docker-down docker-restart \
	docker-status docker-logs docker-logs-all docker-migrate docker-check \
	docker-shell docker-reset-db

docker-config:
	docker compose config --quiet

docker-build:
	docker compose build

docker-up:
	docker compose up -d --build

docker-down:
	docker compose down

docker-restart:
	docker compose restart bot web worker

docker-status:
	docker compose ps

docker-logs:
	docker compose logs --tail=200 -f bot

docker-logs-all:
	docker compose logs --tail=200 -f

docker-migrate:
	docker compose run --rm migrate

docker-check:
	docker compose run --rm bot python -m scripts.check_stage_5_2

docker-shell:
	docker compose run --rm bot sh

# Destructive: removes the PostgreSQL volume and all local Docker data.
docker-reset-db:
	docker compose down -v
