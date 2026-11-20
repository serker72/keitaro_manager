-include .env

# Экспортируем только PROJECT_DATA_DIR (нужен shell-рецептам).
# Остальные переменные docker compose читает из .env сам — глобальный export
# ломает интерполяцию ${PROJECT_DATA_DIR} внутри compose-файла.
export PROJECT_DATA_DIR

# uid/gid пользователя postgres в образе postgres:16-alpine (можно переопределить в .env)
PG_UID ?= 70
PG_GID ?= 70

.DEFAULT_GOAL := help

.PHONY: help init-dirs env env-test up down logs migrate revision lint test

help:
	@echo "Keitaro Manager — доступные команды:"
	@echo "  make env            создать .env (генерирует пароли и AUTH_SECRET_KEY, печатает креды)"
	@echo "  make env-test       создать .env-test (порты +20000, PROJECT_DATA_DIR с суффиксом _test)"
	@echo "  make init-dirs      создать каталоги данных и выставить владельцев"
	@echo "  make up             собрать и запустить стек (postgres + backend + frontend)"
	@echo "  make down           остановить стек"
	@echo "  make logs [сервис]  потоковые логи (например: make logs backend)"
	@echo "  make migrate        применить миграции Alembic"
	@echo "  make revision msg=\"...\"  сгенерировать миграцию"
	@echo "  make lint           ruff + mypy (backend), eslint + typecheck (frontend)"
	@echo "  make test           pytest (backend)"

# Create data directories with proper owners.
# Каталог БД принадлежит пользователю postgres внутри alpine-образа (uid 70),
# поэтому chown выполняется в контейнере от root: локальный пользователь
# не имеет прав на уже инициализированный drwx------ каталог.
init-dirs:
	mkdir -p $(POSTGRES_DATA_DIR) $(LOGS_DATA_DIR)
	@docker run --rm \
		-v "$(POSTGRES_DATA_DIR):/pgdata" \
		-v "$(LOGS_DATA_DIR):/logs" \
		alpine:3 sh -c '\
			if [ -z "$$(ls -A /pgdata 2>/dev/null)" ]; then \
				chown -R $(PG_UID):$(PG_GID) /pgdata; \
				echo "  $(POSTGRES_DATA_DIR) -> $(PG_UID):$(PG_GID)"; \
			else \
				echo "  $(POSTGRES_DATA_DIR) уже инициализирован — владелец не менялся"; \
			fi; \
			chown -R $(APP_UID):$(APP_GID) /logs; \
			echo "  $(LOGS_DATA_DIR) -> $(APP_UID):$(APP_GID)"'

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
