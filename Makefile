.PHONY: up down build logs migrate db-stamp seed test test-backend test-frontend ps

COMPOSE := docker compose

up: build
	$(COMPOSE) up -d postgres
	@echo "Waiting for PostgreSQL..."
	@$(COMPOSE) up -d backend frontend
	@echo "Stack started. API: http://localhost:8000  Frontend: http://localhost:5173"

down:
	$(COMPOSE) down

build:
	$(COMPOSE) build

logs:
	$(COMPOSE) logs -f

ps:
	$(COMPOSE) ps

migrate:
	$(COMPOSE) exec backend alembic upgrade head

# Use when tables already exist but alembic_version is missing (e.g. after tests create_all)
db-stamp:
	$(COMPOSE) exec backend alembic stamp head

seed:
	$(COMPOSE) exec backend python -m app.seed

test: test-backend test-frontend

test-backend:
	$(COMPOSE) exec backend pytest -v

test-frontend:
	cd frontend && npm test
