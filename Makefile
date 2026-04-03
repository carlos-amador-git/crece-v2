# CRECE v2.0 — Development Makefile
# Usage: make [target]

.DEFAULT_GOAL := help
COMPOSE := docker compose
COMPOSE_PROD := docker compose -f docker-compose.yml -f docker-compose.prod.yml
BACKEND_EXEC := $(COMPOSE) exec backend
FRONTEND_EXEC := $(COMPOSE) exec frontend

# ── Colors ────────────────────────────────────────────────────
CYAN := \033[36m
GREEN := \033[32m
YELLOW := \033[33m
RESET := \033[0m

.PHONY: help
help: ## Show this help
	@echo ""
	@echo "$(CYAN)CRECE v2.0$(RESET) — Development Commands"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-20s$(RESET) %s\n", $$1, $$2}'
	@echo ""

# ── Development ───────────────────────────────────────────────
.PHONY: dev
dev: ## Start all services in development mode
	$(COMPOSE) up -d
	@echo "\n$(GREEN)Services running:$(RESET)"
	@echo "  Backend:  http://localhost:8000"
	@echo "  Frontend: http://localhost:3000"
	@echo "  Flower:   http://localhost:5555"
	@echo "  MinIO:    http://localhost:9001"
	@echo "  Postgres: localhost:5432"
	@echo "  Redis:    localhost:6379"

.PHONY: dev-build
dev-build: ## Build and start all services
	$(COMPOSE) up -d --build

.PHONY: build
build: ## Build all Docker images
	$(COMPOSE) build

.PHONY: down
down: ## Stop all services
	$(COMPOSE) down

.PHONY: restart
restart: down dev ## Restart all services

# ── Logs ──────────────────────────────────────────────────────
.PHONY: logs
logs: ## Follow logs for all services
	$(COMPOSE) logs -f

.PHONY: logs-backend
logs-backend: ## Follow backend logs
	$(COMPOSE) logs -f backend

.PHONY: logs-worker
logs-worker: ## Follow Celery worker logs
	$(COMPOSE) logs -f celery-worker

.PHONY: logs-frontend
logs-frontend: ## Follow frontend logs
	$(COMPOSE) logs -f frontend

# ── Database ──────────────────────────────────────────────────
.PHONY: migrate
migrate: ## Run Alembic migrations (upgrade head)
	$(BACKEND_EXEC) alembic upgrade head

.PHONY: migrate-create
migrate-create: ## Create new migration (usage: make migrate-create MSG="add users table")
	$(BACKEND_EXEC) alembic revision --autogenerate -m "$(MSG)"

.PHONY: migrate-down
migrate-down: ## Rollback last migration
	$(BACKEND_EXEC) alembic downgrade -1

.PHONY: seed
seed: ## Run seed data script
	$(BACKEND_EXEC) python -m app.scripts.seed

.PHONY: reset-db
reset-db: ## Destroy database, recreate, and migrate
	@echo "$(YELLOW)WARNING: This will destroy all data$(RESET)"
	$(COMPOSE) down -v
	$(COMPOSE) up -d db redis
	@echo "Waiting for database..."
	@sleep 5
	$(COMPOSE) up -d
	@sleep 3
	$(MAKE) migrate
	@echo "$(GREEN)Database reset complete$(RESET)"

# ── Shell Access ──────────────────────────────────────────────
.PHONY: shell
shell: ## Open bash in backend container
	$(BACKEND_EXEC) bash

.PHONY: shell-db
shell-db: ## Open psql shell
	$(COMPOSE) exec db psql -U $${POSTGRES_USER:-crece} -d $${POSTGRES_DB:-crece}

.PHONY: shell-redis
shell-redis: ## Open redis-cli
	$(COMPOSE) exec redis redis-cli

.PHONY: shell-frontend
shell-frontend: ## Open shell in frontend container
	$(FRONTEND_EXEC) sh

# ── Testing ───────────────────────────────────────────────────
.PHONY: test
test: ## Run backend tests
	$(BACKEND_EXEC) pytest -v

.PHONY: test-cov
test-cov: ## Run backend tests with coverage
	$(BACKEND_EXEC) pytest --cov=app --cov-report=term-missing -v

.PHONY: lint
lint: ## Run linters (ruff + mypy)
	$(BACKEND_EXEC) ruff check .
	$(BACKEND_EXEC) mypy .

.PHONY: format
format: ## Format backend code
	$(BACKEND_EXEC) ruff format .
	$(BACKEND_EXEC) ruff check --fix .

# ── Production ────────────────────────────────────────────────
.PHONY: prod
prod: ## Start production stack
	$(COMPOSE_PROD) up -d

.PHONY: prod-build
prod-build: ## Build production images
	$(COMPOSE_PROD) build

.PHONY: prod-down
prod-down: ## Stop production stack
	$(COMPOSE_PROD) down

.PHONY: prod-logs
prod-logs: ## Follow production logs
	$(COMPOSE_PROD) logs -f

# ── Utilities ─────────────────────────────────────────────────
.PHONY: ps
ps: ## Show running containers and their status
	$(COMPOSE) ps

.PHONY: clean
clean: ## Remove all containers, volumes, and images
	@echo "$(YELLOW)WARNING: This will remove all CRECE data$(RESET)"
	$(COMPOSE) down -v --rmi local --remove-orphans

.PHONY: prune
prune: ## Remove dangling Docker resources
	docker system prune -f
	docker volume prune -f

.PHONY: env
env: ## Copy .env.example to .env if it doesn't exist
	@[ -f .env ] && echo "$(YELLOW).env already exists$(RESET)" || (cp .env.example .env && echo "$(GREEN).env created from .env.example$(RESET)")
