COMPOSE = docker compose \
	-f compose.yaml \
	-f compose.backup.yaml \
	-f compose.delivery.yaml \
	-f compose.marketing.yaml

.PHONY: docker-config docker-build docker-up docker-down docker-restart \
	docker-status docker-logs docker-logs-all docker-migrate docker-check \
	docker-check-dependencies docker-shell docker-reset-db stabilize-check \
	stabilize-apply release-check release-check-runtime deploy

docker-config:
	$(COMPOSE) config --quiet

docker-build:
	$(COMPOSE) build

docker-up:
	$(COMPOSE) up -d --build

docker-down:
	$(COMPOSE) down

docker-restart:
	$(COMPOSE) restart bot web worker delivery-worker broadcast-worker

docker-status:
	$(COMPOSE) ps

docker-logs:
	$(COMPOSE) logs --tail=200 -f bot

docker-logs-all:
	$(COMPOSE) logs --tail=200 -f

docker-migrate:
	$(COMPOSE) run --rm migrate

docker-check:
	$(COMPOSE) run --rm bot python -m scripts.check_project
	$(COMPOSE) run --rm bot python -m scripts.check_migration_head

docker-check-dependencies:
	$(COMPOSE) run --rm bot python -m scripts.check_dependencies

docker-shell:
	$(COMPOSE) run --rm bot sh

# Destructive: removes PostgreSQL, Redis and backup volumes.
docker-reset-db:
	$(COMPOSE) down -v


stabilize-check:
	python3 -m scripts.stabilize_project

stabilize-apply:
	python3 -m scripts.stabilize_project --apply

release-check:
	python3 -m scripts.release_check

release-check-runtime:
	$(COMPOSE) exec -T web python -m scripts.release_check --runtime-only


deploy:
	python3 -m scripts.deploy
