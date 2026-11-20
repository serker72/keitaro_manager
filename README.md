# Keitaro Manager

Веб-приложение для управления кампаниями и потоками (flows) трекера Keitaro через Admin API:
создание кампании с двумя потоками «из коробки» и редактирование распределения офферов по весам
с последующей отправкой в трекер.

Монорепозиторий: `backend/` (FastAPI) + `frontend/` (Nuxt 3), PostgreSQL, Docker Compose.

---

## Стек

| Слой | Технологии |
|------|-----------|
| Backend | Python 3.13, FastAPI, SQLAlchemy 2.0 (async), psycopg3, Alembic, Pydantic 2, httpx, Dishka, uv |
| Backend-качество | `ruff` (lint + format), `mypy --strict` (с плагином `pydantic.mypy`), `pytest` |
| Frontend | Nuxt 3, Vue 3, TypeScript, TailwindCSS |
| Frontend-качество | `@nuxt/eslint` (ESLint 9 flat config), Prettier + `prettier-plugin-tailwindcss`, `nuxi typecheck` |
| Инфраструктура | Docker Compose (PostgreSQL + backend + frontend), Makefile, `.env` |

---

## Архитектура

### Backend

```
backend/src/
├── core/           # config (pydantic-settings), database (engine/sessionmaker), ioc (Dishka)
├── models/         # SQLAlchemy 2.0 модели
├── schemas/        # Pydantic-схемы Keitaro API + DTO для фронтенда
├── clients/        # KeitaroClient (httpx.AsyncClient)
├── repositories/   # доступ к данным (Repository Pattern)
├── services/       # бизнес-логика (Service Layer)
└── api/routes/     # тонкие роутеры (DishkaRoute + FromDishka)
```

**Repository Pattern.** `BaseRepository` инкапсулирует CRUD поверх `AsyncSession`;
`CampaignRepository` и `StreamOfferRepository` добавляют доменные запросы
(`get_by_keitaro_id`, `get_by_stream`, `upsert_many` через
`postgresql.insert(...).on_conflict_do_update`).

**Service Layer.** Вся оркестрация — в сервисах, роутеры только принимают схему, вызывают метод
и возвращают ответ:

* `DictionaryService` — параллельная (`asyncio.gather`) загрузка доменов, групп кампаний,
  источников трафика и офферов.
* `CampaignService` («Создаватор») — генерация уникального `alias`, `POST /campaigns`,
  создание Потока 1 (`type=regular`, `schema=redirect`, фильтр по стране → `https://www.google.com`)
  и Потока 2 (`type=default`, `schema=landings`, выбранный оффер с `share=100`),
  сохранение кампании и начального состояния оффера в PostgreSQL.
* `StreamEditorService` («Редактор») — синхронизация с трекером, пересчёт весов, отправка в Keitaro.

**IoC (Dishka).** `AppProvider`:
* `Scope.APP` — `Settings`, `AsyncEngine`, `async_sessionmaker`, `httpx.AsyncClient`
  (контекстный генератор — пул закрывается при остановке приложения), `KeitaroClient`;
* `Scope.REQUEST` — `AsyncSession` (commit при успехе, rollback при исключении), репозитории, сервисы.

Контейнер создаётся на уровне модуля и подключается через `setup_dishka(container, app)`
(Starlette запрещает добавлять middleware после старта приложения); закрывается в `lifespan`.

### Почему без Redis и брокеров

Состояние офферов — это проекция состояния трекера. Любой кэш или очередь создавали бы
окно рассинхрона с Keitaro: пользователь видит одно, трекер исполняет другое. Источник истины —
Admin API Keitaro; локально хранится только последнее подтверждённое состояние
(`StreamOfferState`) плюс метаданные, которых в Keitaro нет (`is_pinned`, `is_removed`).
Это исключает лишнюю инфраструктуру и целый класс багов «кэш разошёлся с реальностью».

### Алгоритм пересчёта весов

Чистая функция `recalculate_weights` (backend) с зеркальной реализацией на фронтенде
(`frontend/utils/weights.ts`):

1. Запиненные активные офферы сохраняют свой вес.
2. `remaining = 100 - sum(pinned_shares)` делится поровну между незапиненными активными:
   `base = remaining // count`, первым `mod` офферам добавляется `+1%`
   (например `34/33/33`; при одном запиненном на `25%` — `38/37`).
3. Если запинено 100% — `remaining = 0`, все незапиненные получают `0%`.
4. Удалённые офферы всегда `0%` и не участвуют в делении.

`PUSH TO KT` отправляет `PUT /streams/{id}` только если сумма весов активных офферов ровно `100%`,
иначе бэкенд возвращает `422`. В трекер уходят только активные офферы (`is_removed=false`).

### Удалённые офферы

`StreamOfferState.is_removed` — единственный способ «удалить» оффер в приложении.
При `REMOVE` строка остаётся в БД с `share=0`; при `FETCH STREAMS FROM KT` оффер, исчезнувший
в трекере, не удаляется, а помечается `is_removed=True, share=0`. Это позволяет восстановить
(`BRING BACK`) оффер вместе с его настройками.

### Dirty State на клиенте

В компоненте `StreamOffers.vue` живут два состояния: `savedOffers` (с бэкенда) и `draftOffers`
(рабочая копия). Любое действие (`ADD`, `REMOVE`, `BRING BACK`, ручной `Share`, `PIN`)
обновляет только draft и локально пересчитывает веса. При наличии расхождений (`isDirty`)
блок подсвечивается жёлтым, появляются `PUSH TO KT` и `CANCEL` (мгновенный откат к `savedOffers`),
а при сумме весов ≠ 100% кнопка отправки блокируется.

---

## Авторизация

> Авторизация добавлена **проактивно** (в ТЗ её не было): приложение проксирует запросы к Admin API
> Keitaro с API-ключом, поэтому публичный доступ к UI означал бы публичный доступ к трекеру.

**Дефолтные креды:** `admin` / `change_me` (значения по умолчанию в `.env.example`).
`make env` генерирует случайный `USER_PASSWORD` и печатает его в консоль — если нужен пароль
из коробки, поставьте в `.env` `USER_PASSWORD=change_me`.

Реализация — **stateless, без БД**:

* `AuthService` (`backend/src/services/auth.py`) сравнивает логин и пароль из `Settings`
  через `secrets.compare_digest()` (защита от timing-атак) и выпускает подписанный JWT (PyJWT, HS256).
* Токен кладётся в **httpOnly cookie** (`SameSite=Lax`, TTL `AUTH_TOKEN_TTL_MINUTES`, по умолчанию 12 ч).
  Альтернативно принимается `Authorization: Bearer <token>`.
* Эндпоинты: `POST /api/auth/login`, `POST /api/auth/logout`, `GET /api/auth/me`.
* Роутеры `dictionaries`, `campaigns`, `streams` защищены единой зависимостью
  `verify_auth` на уровне `APIRouter` (`dependencies=[Depends(verify_auth)]`).
* Frontend: страница `/login`, глобальный `middleware/auth.global.ts` (редирект на `/login`
  без валидной сессии), кнопка `Logout` в шапке.

Переменные окружения: `USER_LOGIN`, `USER_PASSWORD`, `AUTH_SECRET_KEY` (генерируется `make env`
через `openssl rand -hex 32`).

---

## Запуск

### Требования

* Docker + Docker Compose
* `make`, `openssl`
* (для локальных линтеров/тестов) `uv`, Node.js 22+

### Шаги

```bash
make env            # создаёт .env, генерирует POSTGRES_PASSWORD, USER_PASSWORD, AUTH_SECRET_KEY
                    # и печатает логин/пароль пользователя в консоль
```

Заполнить в `.env` доступы к трекеру:

```dotenv
KEITARO_BASE_URL=https://your-keitaro-host/admin
KEITARO_API_KEY=<api-key>
```

```bash
make init-dirs      # создаёт POSTGRES_DATA_DIR и LOGS_DATA_DIR с правами APP_UID:APP_GID
make up             # docker compose up -d --build (postgres + backend + frontend)
make migrate        # alembic upgrade head внутри контейнера backend
```

Приложение: **http://127.0.0.1:3000** (порт задаётся `FRONTEND_PORT_HOST`).
Backend: `http://127.0.0.1:33000` (`BACKEND_PORT_HOST`), документация — `/docs`.

Вход: логин `USER_LOGIN` и пароль `USER_PASSWORD` из `.env` (по умолчанию `admin` / `change_me`).

### Основные команды Makefile

| Команда | Действие |
|---------|----------|
| `make env` | создать `.env`: генерирует `POSTGRES_PASSWORD`, `USER_PASSWORD`, `AUTH_SECRET_KEY`, печатает креды |
| `make env-test` | создать `.env-test` из `.env`: новые пароли и секрет, `PROJECT_DATA_DIR` + `_test`, хост-порты +20000 |
| `make init-dirs` | создать каталоги данных с правами `APP_UID:APP_GID` |
| `make up` / `make down` | поднять / остановить стек |
| `make logs` / `make logs backend` | потоковые логи (с фильтром по сервису) |
| `make migrate` | применить миграции Alembic |
| `make revision msg="..."` | сгенерировать миграцию по моделям |
| `make lint` | `ruff check` + `ruff format --check` + `mypy src/` + `eslint` + `nuxi typecheck` |
| `make test` | `pytest` |

### Локальная разработка (без Docker)

```bash
# backend
cd backend
uv sync
POSTGRES_HOST=localhost uv run alembic upgrade head
POSTGRES_HOST=localhost uv run uvicorn src.main:app --reload --port 33000

# frontend
cd frontend
npm ci
NUXT_BACKEND_URL=http://localhost:33000 npm run dev
```

Фронтенд проксирует `/api/**` на бэкенд через `routeRules` в `nuxt.config.ts`,
поэтому CORS в dev-режиме не мешает.

---

## Проверка качества

```bash
make lint    # backend: ruff + mypy --strict; frontend: eslint + vue-tsc
make test    # backend: pytest (алгоритм весов: pin, pin=100%, removed, restore)
```

---

## API

| Метод | Путь | Назначение |
|-------|------|-----------|
| `POST` | `/api/auth/login` | вход (выставляет httpOnly cookie с JWT) |
| `POST` | `/api/auth/logout` | выход (удаляет cookie) |
| `GET` | `/api/auth/me` | текущий пользователь (401 без сессии) |
| `GET` | `/api/dictionaries` | домены, группы кампаний, источники трафика, офферы |
| `GET` | `/api/campaigns` | список локально сохранённых кампаний |
| `POST` | `/api/campaigns` | создание кампании + Flow 1 + Flow 2 |
| `GET` | `/api/campaigns/{id}/streams?sync=true` | потоки кампании (опционально — синхронизация с Keitaro) |
| `PUT` | `/api/campaigns/{id}/streams/{stream_id}/push` | отправка офферов в Keitaro |

Ошибки трекера (`400/401/402/404/406/500`) маппятся в соответствующие HTTP-ответы,
ошибки бизнес-валидации — в `422`, отсутствие/недействительность сессии — в `401`.

---

## Использование ИИ-инструментов

Код генерировался с помощью ИИ-ассистентов (**KodaCode**, **Veai**) под архитектурным контролем
автора: структура слоёв, границы ответственности сервисов и репозиториев, схема хранения
состояния офферов, алгоритм пересчёта весов и подход к Dirty State задавались вручную
и фиксировались в плане разработки (`docs/design-plan.md`).

ИИ применялся для: каркаса проекта и инфраструктуры, шаблонного CRUD-кода репозиториев,
Pydantic-схем по `docs/openapi.yaml`, вёрстки компонентов на TailwindCSS и написания тестов.
Все спорные места (расхождения спецификации с живым API — например `group_id` как `string`
в запросе и `integer` в ответе, `payload` фильтра как массив, а не строка) проверялись
запросами к реальному стенду Keitaro и исправлялись вручную. Каждый этап завершался прогоном
линтеров, type-check и тестов.
