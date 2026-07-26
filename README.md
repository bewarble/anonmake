# AnonMake

Telegram bot for anonymous questions and answers.

## Local development with SQLite

```bash
cp .env.example .env
# Set BOT_TOKEN in .env
python3 -m pip install -r requirements.txt
python3 -m scripts.migrate
python3 -m app.main
```

The default local database is `data/anonmake.db`.

## Docker Compose with PostgreSQL

Set `BOT_TOKEN` and a strong `POSTGRES_PASSWORD` in `.env`, then run:

```bash
docker compose up -d --build
docker compose logs -f bot
```

Stop services without deleting the database volume:

```bash
docker compose down
```

## Database migrations

```bash
python3 -m scripts.migrate
alembic current
alembic history
```

Stage 3 SQLite databases are detected and stamped at the initial Alembic
revision without deleting their existing users, questions, or answers.

## Health check

```bash
python3 -m scripts.healthcheck
```

## Stage 4.1 verification

```bash
python3 -m scripts.check_stage_4_1
```
