-include .env

export

.PHONY: init-dirs env env-test up down logs migrate revision lint test

# Create data directories with proper permissions
init-dirs:
	mkdir -p $(POSTGRES_DATA_DIR) $(LOGS_DATA_DIR)
	chown -R $(APP_UID):$(APP_GID) $(POSTGRES_DATA_DIR)

# Generate .env from .env.example
env:
	@if [ ! -f .env ]; then cp .env.example .env; echo ".env created"; else echo ".env already exists"; fi

# Generate .env-test with port shift +20000
env-test:
	cp .env.example .env-test
	sed -i 's/^POSTGRES_PORT_HOST=\([0-9]*\)/POSTGRES_PORT_HOST=$$((\1 + 20000))/' .env-test
	sed -i 's/^BACKEND_PORT_HOST=\([0-9]*\)/BACKEND_PORT_HOST=$$((\1 + 20000))/' .env-test
	sed -i 's/^FRONTEND_PORT_HOST=\([0-9]*\)/FRONTEND_PORT_HOST=$$((\1 + 20000))/' .env-test

# Docker compose commands
up:
	docker compose up -d --build

down:
	docker compose down

logs:
	docker compose logs -f $(filter-out $@,$(MAKECMDGOALS))

# Alembic migrations
migrate:
	cd backend && uv run alembic upgrade head

revision:
	cd backend && uv run alembic revision --autogenerate -m "$(msg)"

# Unified linting
lint:
	cd backend && uv run ruff check . && uv run ruff format --check . && uv run mypy src/
	cd frontend && npx eslint . && npx nuxi typecheck

# Run tests
test:
	cd backend && uv run pytest
