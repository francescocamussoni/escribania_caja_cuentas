.PHONY: up down build logs migrate db-stamp seed test test-backend test-frontend ps \
	deploy-aws smoke-aws validate-infra validate-infra-contract validate-outputs-security \
	check-secrets preprod-checklist

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

# AWS production deploy (specs/002-aws-deploy)
# Examples:
#   make deploy-aws ADMIN_USER=prod-admin ADMIN_PASS='...'
#   make deploy-aws ARGS="--skip-terraform"
deploy-aws:
	./scripts/deploy-aws.sh $(ARGS)

smoke-aws:
	./scripts/smoke-aws.sh

validate-infra-contract:
	./scripts/validate-infra-contract.sh

validate-outputs-security:
	./scripts/validate-outputs-security.sh

validate-infra: validate-infra-contract validate-outputs-security
	cd infra && terraform fmt -check -recursive .
	cd infra && terraform init -backend=false -input=false
	cd infra && terraform validate

check-secrets:
	./scripts/check-secrets.sh

preprod-checklist:
	./scripts/run-preprod-checklist.sh
