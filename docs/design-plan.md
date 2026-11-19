
### Технологический стек и стандарты качества

* **Backend:** Python 3.13+, FastAPI, SQLAlchemy 2.0 (async), `psycopg[binary]` (psycopg3), Alembic, Pydantic 2.0, `pydantic-settings`, `httpx`, `dishka`. Менеджер пакетов — `uv`.
* **Архитектура Backend:** Repository Pattern, Service Layer, IoC-контейнер (`Dishka`), тонкие роутеры. Redis и брокеры сообщений сознательно не используются, чтобы исключить рассинхрон с внешним API Keitaro и избыточную сложность.
* **Линтеры Backend:** `ruff` (линтинг и форматирование) + `mypy` (строгая проверка типов с плагином `pydantic.mypy`).
* **Frontend:** Nuxt 3, Vue 3, TypeScript, TailwindCSS.
* **Линтеры Frontend:** `@nuxt/eslint` (ESLint 9 Flat Config), `Prettier` + `prettier-plugin-tailwindcss`, `nuxi typecheck` (`vue-tsc`).
* **Инфраструктура:** Монорепозиторий (`backend/`, `frontend/`), `docker-compose.yml` (PostgreSQL + Backend + Frontend), `Makefile`, `.env.example`.

---

### Этап 1. Инициализация монорепозитория и окружения

1. **Структура корня:** создать директории `backend/`, `frontend/`, а также файлы `docker-compose.yml`, `Makefile`, `.env.example`, `.gitignore`.
2. **Конфигурация `.env.example`:** оформить на базе шаблона проекта, очистив от неиспользуемых сервисов (Redis, RabbitMQ, MinIO) и заменив технические названия БД/пользователя:
* Блок окружения: `PROJECT_ENVIRONMENT=loc`, `PROJECT_NAME=keitaro_manager`, `APP_UID=1000`, `APP_GID=1000`.
* Директории данных (bind mounts): `PROJECT_DATA_DIR=/opt/keitaro_manager`, `POSTGRES_DATA_DIR="${PROJECT_DATA_DIR}/db"`, `LOGS_DATA_DIR="${PROJECT_DATA_DIR}/logs"`.
* PostgreSQL: `POSTGRES_HOST=postgres`, `POSTGRES_PORT=5432`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`.
* Keitaro: `KEITARO_BASE_URL`, `KEITARO_API_KEY`.
* Хост-порты (публикация на `127.0.0.1`, со сдвигом `+20000` для тестового окружения): `POSTGRES_PORT_HOST`, `BACKEND_PORT_HOST`, `FRONTEND_PORT_HOST`.


3. **Создание `Makefile**` (с чтением `.env`):
* `make init-dirs` — создание `POSTGRES_DATA_DIR` и `LOGS_DATA_DIR` с правами `APP_UID:APP_GID`.
* `make env` / `make env-test` — генерация `.env` из `.env.example` (для `env-test` со сдвигом хост-портов на `+20000`).
* `make up` / `make down` / `make logs` — запуск, остановка и просмотр потоковых логов `docker compose` (с поддержкой фильтра по сервису).
* `make migrate` / `make revision msg="..."` — управление миграциями Alembic.
* `make lint` — единый прогон `ruff`, `mypy` (backend) и `eslint`, `nuxi typecheck` (frontend).
* `make test` — запуск `uv run pytest`.


4. **Инициализация Backend (`uv`):**
* В `backend/` выполнить `uv init --python 3.13` и установить зависимости:
`uv add fastapi uvicorn "sqlalchemy[asyncio]" "psycopg[binary]" alembic httpx pydantic-settings dishka`
`uv add --dev ruff mypy pytest`
* Настроить секции `[tool.ruff]` и `[tool.mypy]` в `backend/pyproject.toml`.



---

### Этап 2. Слой данных (Models, Alembic & Repository)

1. **Ядро БД (`backend/src/core/`):**
* `config.py` — загрузка настроек через `pydantic-settings`, формирование строки подключения с диалектом `postgresql+psycopg://`.
* `database.py` — фабрика `create_async_engine` и `async_sessionmaker`.


2. **Модели SQLAlchemy 2.0 (`backend/src/models/`):**
* `CampaignRecord` — локальный аудит кампаний (`id`, `keitaro_campaign_id`, `name`, `geo`, `created_at`, `updated_at`).
* `StreamOfferState` — хранение последнего подтвержденного состояния офферов потока и метаданных, которых нет в Keitaro: `id`, `campaign_id`, `stream_id`, `offer_id`, `offer_name`, `share` (`int`), `is_pinned` (`bool`, default `False`), `is_removed` (`bool`, default `False`), `updated_at`. Флаг `is_published` в БД не хранится — черновик редактирования живет на фронтенде.


3. **Миграции:** инициализировать `alembic init -t async alembic`, сгенерировать и применить первую миграцию.
4. **Репозитории (`backend/src/repositories/`):**
* `BaseRepository` — базовые асинхронные CRUD-операции поверх `AsyncSession`.
* `CampaignRepository` — работа с `CampaignRecord`.
* `StreamOfferRepository` — получение состояния офферов по `stream_id` / `campaign_id`, массовое обновление (upsert) после синхронизации или отправки в Keitaro.



---

### Этап 3. Интеграционный слой (Keitaro API Client & Schemas)

1. **Pydantic-схемы (`backend/src/schemas/keitaro.py`)** строго по `openapi.yaml`:
* Справочники: `Domain`, `Group`, `Source`, `Offer`.
* Кампании и потоки: `CampaignRequest`, `Campaign`, `StreamRequest`, `StreamRequestPut`, `Stream`, `FilterStreamRequest`, `OfferStreamRequest`, `OfferStream`.
* Учесть нюансы спецификации: `alias` обязателен при создании кампании (`CampaignCreateRequired`); проверить и корректно сериализовать тип `group_id` (в запросе описан как `string`, в ответе — `integer`).

2. **Асинхронный клиент (`backend/src/clients/keitaro.py`):**
* Класс `KeitaroClient`, принимающий `httpx.AsyncClient` с базовым путем `/admin_api/v1` и заголовком `Api-Key`.
* Централизованная обработка кодов ошибок (`400`, `401`, `402`, `404`, `406`, `500`).
* Реализация методов:
* Справочники: `GET /domains`, `GET /groups?type=campaigns`, `GET /traffic_sources`, `GET /offers`.
* Метаданные (для первичной сверки точных ключей на живом стенде): `GET /stream_filters`, `GET /streams_actions`.
* Кампании: `GET /campaigns`, `POST /campaigns`.
* Потоки: `GET /campaigns/{id}/streams`, `POST /streams`, `PUT /streams/{id}`.

---

### Этап 4. Слой бизнес-логики (Service Layer)

Вся бизнес-логика и оркестрация выносятся в сервисные классы (`backend/src/services/`).

1. **`DictionaryService`:**
* Параллельная загрузка доменов, групп кампаний, источников трафика и офферов через `asyncio.gather()`.

2. **`CampaignService` (Создаватор):**
* Генерация валидного уникального `alias` для новой кампании.
* Вызов `POST /campaigns` с переданными `domain_id`, `group_id`, `traffic_source_id`, `state="active"`, `type="position"`.
* Создание Потока 1 (`POST /streams`): `type="regular"`, `schema="redirect"`, фильтр по стране (`mode="accept"`, `payload=[geo_code]`), редирект на `[https://google.com](https://google.com)`.
* Создание Потока 2 (`POST /streams`): `type="default"`, `schema="landings"`, привязка выбранного `offer_id` с `share=100`, `state="active"`.
* Сохранение записи о кампании и начального состояния оффера в PostgreSQL через репозитории.


3. **`StreamEditorService` (Редактор):**
* **Синхронизация (`fetch_streams_from_kt`):** запрашивает `GET /campaigns/{id}/streams` и мержит с `StreamOfferState` из БД. Если оффер был в локальной БД, но исчез в Keitaro — он не удаляется, а помечается `is_removed=True`, `share=0` для возможности восстановления.

* **Алгоритм пересчета весов (чистая функция с unit-тестами):**
* Запиненные активные офферы (`is_pinned=True`) сохраняют свой вес.
* Остаток `remaining = 100 - sum(pinned_shares)` делится поровну между незапиненными активными офферами: `base = remaining // count`, остаток `mod = remaining % count`; первым `mod` офферам добавляется `+1%` (например, `34% / 33% / 33%` для 3 офферов, `38% / 37%` при одном запиненном на `25%`).

* **Кейс `pin` одного элемента на 100%:** `remaining = 0`; все вновь добавленные или восстановленные (`BRING BACK`) офферы получают `0%` до снятия `pin` или ручного уменьшения веса.

* **Отправка в Keitaro (`push_stream_to_kt`):**
* Строгая валидация: сумма `share` всех активных офферов (`is_removed=False`) должна быть ровно `100%` (иначе возвращается ошибка валидации `422`).
* Отправка в `PUT /streams/{id}` только активных офферов (`is_removed=False`).


* Сохранение финального состояния в PostgreSQL (включая `is_pinned` и `is_removed=True` с `share=0`).


---

### Этап 5. IoC-контейнер (Dishka), тонкие роутеры и контроль качества Backend

1. **DI-контейнер (`backend/src/core/ioc.py`):**
* `AppProvider(Provider)` со скоупами:
* `Scope.APP`: `Settings`, `AsyncEngine`, `async_sessionmaker`, `httpx.AsyncClient` (контекстный генератор `AsyncIterable` для корректного закрытия пула), `KeitaroClient`.
* `Scope.REQUEST`: `AsyncSession` (контекстный генератор с закрытием после запроса), `CampaignRepository`, `StreamOfferRepository`, `DictionaryService`, `CampaignService`, `StreamEditorService`.

* Подключение через `setup_dishka(container, app)` в `backend/src/main.py` и закрытие контейнера в `lifespan`.


2. **Тонкие роутеры (`backend/src/api/routes/`):**
* Использование `APIRouter(route_class=DishkaRoute)` и инъекция сервисов через `FromDishka[...]`. Роутеры только принимают Pydantic-схемы, вызывают метод сервиса и возвращают ответ:
* `GET /api/dictionaries`
* `GET /api/campaigns`
* `POST /api/campaigns`
* `GET /api/campaigns/{id}/streams` (чтение из БД + опциональный флаг `sync=true` для `FETCH STREAMS FROM KT`)
* `PUT /api/campaigns/{id}/streams/{stream_id}/push` (`PUSH TO KT`)


3. **Настройка `main.py`:** CORS для фронтенда, глобальные обработчики исключений (маппинг ошибок Keitaro API и бизнес-валидации в понятные HTTP-ответы).
4. **Проверка качества:** unit-тесты на алгоритм пересчета весов (включая `pin` и кейс со 100%) через `pytest`, прогон `ruff check`, `ruff format --check` и `mypy src/` до полного отсутствия ошибок.

---

### Этап 6. Frontend (Nuxt 3 + TypeScript + TailwindCSS)

1. **Настройка проекта:** инициализация Nuxt 3 в `frontend/`, подключение TailwindCSS, `@nuxt/eslint`, Prettier. Настройка `routeRules` в `nuxt.config.ts` для проксирования `/api/**` на бэкенд.
2. **Типизированный API-слой:** `composables/useApi.ts` на базе `$fetch` и TypeScript-интерфейсы под схемы FastAPI.
3. **Экран 1 — «Создаватор кампаний»:**
* Форма с полями: название кампании, GEO-код страны, селекты домена, группы, источника трафика и оффера (загружаются из `GET /api/dictionaries`).
* Индикация загрузки, обработка ошибок API, переход к созданной кампании после успеха.


4. **Экран 2 — «Редактор кампаний»:**
* Список кампаний с переходом в конкретную кампанию.
* Верхняя панель кампании: кнопки `FETCH STREAMS FROM KT` (принудительная синхронизация с трекером) и `VIEW IN KT` (внешняя ссылка на кампанию в Keitaro).


* **Два режима отображения потоков:**
* Поток без офферов (например, `Flow 1` с редиректом на Google): компактная строка с названием, фильтром, `stream_id` и кликами.


* Поток с офферами (`Flow 2`): таблица с колонками `Offer` (название + ссылка `preview`), `Share`, `Stats`, `Trends`, `Actions`.




* **Управление состоянием (Dirty State на клиенте):**
* Хранение двух состояний: `savedOffers` (с бэкенда) и `draftOffers` (рабочая копия).
* Любое изменение (`ADD`, `REMOVE`, `BRING BACK`, ручной ввод `Share`, переключение `Pin`) мгновенно обновляет `draftOffers` и локально пересчитывает веса по той же формуле, что и на бэкенде.
* При наличии несохраненных изменений (`isDirty`) блок потока подсвечивается светло-желтым фоном, в шапке появляются кнопки `PUSH TO KT` и `CANCEL` (мгновенный откат `draftOffers` к `savedOffers`).
* Если сумма активных весов `!= 100%`, выводится предупреждение и кнопка `PUSH TO KT` блокируется.

* **Строки таблицы и добавление:**
* Активные офферы: кликабельный процент `Share` для ручного ввода, иконка-переключатель `Pin`, кнопка `REMOVE`.
* Удаленные офферы (как локально, так и в Keitaro): отображаются внизу таблицы приглушенным цветом с пометкой `(removed)`, весом `0%` и кнопкой `BRING BACK`.
* Внизу таблицы: выпадающий список доступных офферов + кнопка `ADD`.


5. **Проверка качества:** прогон `npm run lint` и `npx nuxi typecheck`.

---

### Этап 7. Контейнеризация, сквозная проверка и README

1. **Docker:** написать `Dockerfile` для `backend` (на базе `uv`, с учетом `APP_UID`/`APP_GID`) и `frontend`, объединить с PostgreSQL в `docker-compose.yml`.
2. **Сквозное тестирование на живом стенде Keitaro:**
* Создать кампанию -> проверить в админке Keitaro домен, группу, источник, `Flow 1` (фильтр по стране -> Google) и `Flow 2` (оффер 100%).
* В редакторе проверить добавление офферов, пересчет `34/33/33`, фиксацию `Pin`, кейс `Pin = 100%`, `REMOVE` -> `PUSH TO KT` -> `BRING BACK`, откат через `CANCEL` и синхронизацию `FETCH STREAMS FROM KT` после ручного удаления оффера в самой админке Keitaro.


3. **Документация (`README.md`):**
* Архитектура решения (Repository + Service Layer + Dishka, почему без Redis, как устроен Dirty State и хранение удаленных офферов).
* Пошаговый запуск через `Makefile` (`make env` -> заполнить `KEITARO_API_KEY` -> `make init-dirs` -> `make up` -> `make migrate`).
* Команды запуска линтеров и тестов (`make lint`, `make test`).
* Блок о том, как использовались ИИ-инструменты (KodaCode/Veai) при генерации кода под твоим архитектурным контролем.


