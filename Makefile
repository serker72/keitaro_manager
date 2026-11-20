-include .env

# Экспортируем только PROJECT_DATA_DIR (нужен shell-рецептам).
# Остальные переменные docker compose читает из .env сам — глобальный export
# ломает интерполяцию ${PROJECT_DATA_DIR} внутри compose-файла.
export PROJECT_DATA_DIR

.PHONY: init-dirs env env-test up down logs migrate revision lint test

# Create data directories with proper permissions
init-dirs:
	mkdir -p $(POSTGRES_DATA_DIR) $(LOGS_DATA_DIR)
	chown -R $(APP_UID):$(APP_GID) $(POSTGRES_DATA_DIR)

# Generate .env from .env.example with generated POSTGRES_PASSWORD, USER_PASSWORD, AUTH_SECRET_KEY
env:
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		sed -i "s/^POSTGRES_PASSWORD=.*/POSTGRES_PASSWORD=$$(openssl rand -hex 24)/" .env; \
		sed -i "s/^USER_PASSWORD=.*/USER_PASSWORD=$$(openssl rand -base64 18 | tr -d '/+=' | cut -c1-20)/" .env; \
		sed -i "s/^AUTH_SECRET_KEY=.*/AUTH_SECRET_KEY=$$(openssl rand -hex 32)/" .env; \
		echo ".env created"; \
		echo "  POSTGRES_PASSWORD  — сгенерирован"; \
		echo "  AUTH_SECRET_KEY    — сгенерирован"; \
		echo "  USER_LOGIN:    $$(grep '^USER_LOGIN=' .env | cut -d= -f2-)"; \
		echo "  USER_PASSWORD: $$(grep '^USER_PASSWORD=' .env | cut -d= -f2-)"; \
	else echo ".env already exists"; fi

# Generate .env-test from .env: new secrets, PROJECT_DATA_DIR suffix _test, ports +20000
env-test:
	@if [ ! -f .env ]; then $(MAKE) --no-print-directory env; fi
	cp .env .env-test
	sed -i "s/^POSTGRES_PASSWORD=.*/POSTGRES_PASSWORD=$$(openssl rand -hex 24)/" .env-test
	sed -i "s/^USER_PASSWORD=.*/USER_PASSWORD=$$(openssl rand -base64 18 | tr -d '/+=' | cut -c1-20)/" .env-test
	sed -i "s/^AUTH_SECRET_KEY=.*/AUTH_SECRET_KEY=$$(openssl rand -hex 32)/" .env-test
	sed -i 's#^PROJECT_DATA_DIR=\(.*\)#PROJECT_DATA_DIR=\1_test#' .env-test
	awk -F= '/^[A-Z_]*_PORT_HOST=/{print $$1"="$$2+20000; next} {print}' .env-test > .env-test.tmp && mv .env-test.tmp .env-test
	@echo ".env-test created"
	@echo "  USER_LOGIN:    $$(grep '^USER_LOGIN=' .env-test | cut -d= -f2-)"
	@echo "  USER_PASSWORD: $$(grep '^USER_PASSWORD=' .env-test | cut -d= -f2-)"

# Docker compose commands
up:
	docker compose up -d --build

down:
	docker compose down

logs:
	docker compose logs -f $(filter-out $@,$(MAKECMDGOALS))

# Alembic migrations (выполняются в контейнере backend — POSTGRES_HOST=postgres)
migrate:
	docker compose exec backend alembic upgrade head

revision:
	docker compose exec backend alembic revision --autogenerate -m "$(msg)"

# Unified linting
lint:
	cd backend && uv run ruff check . && uv run ruff format --check . && uv run mypy src/
	cd frontend && npx eslint . && npx nuxi typecheck

# Run tests
test:
	cd backend && uv run pytest
