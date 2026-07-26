.PHONY: install migrate check run docker-up docker-down docker-logs

install:
	python3 -m pip install -r requirements.txt

migrate:
	python3 -m scripts.migrate

check:
	python3 -m scripts.check_stage_4_1

run: migrate
	python3 -m app.main

docker-up:
	docker compose up -d --build

docker-down:
	docker compose down

docker-logs:
	docker compose logs -f bot
