# Реализация US-B2B-02: Создание SKU с управлением статусом товара и отправкой событий в Moderation

## Описание
Реализован endpoint `POST /api/v1/skus` для добавления SKU к товарам продавца. При добавлении первого SKU товар автоматически переводится в статус `ON_MODERATION` и отправляется событие `PRODUCT_CREATED` в Moderation Service через Outbox-паттерн. При последующих изменениях товара (re-moderation) отправляется событие `PRODUCT_EDITED` со снимками состояния до и после.

Реализация строго соответствует спецификациям `b2b/openapi.yaml` и `moderation/openapi.yaml`.

## Соответствие OpenAPI спецификации

### b2b/openapi.yaml
- Путь: `POST /api/v1/skus`
- Схема запроса: `SKUCreateRequest` с полями `product_id`, `name`, `price` (обязательные), `stock_quantity`, `article`, `discount`, `cost_price`, `images`, `characteristics` (опциональные)
- Схема ответа: `SKUResponse` с полным набором полей: `discount`, `cost_price`, `active_quantity`, `reserved_quantity`, `updated_at`, `images[].id/ordering`, `characteristics[].id`
- Код ответа: `201 Created`
- Аутентификация: заголовок `Authorization: Bearer <token>`
- Начальный статус товара: `CREATED` (в соответствии с enum `ProductStatus`)

### moderation/openapi.yaml
- Событие `PRODUCT_CREATED`: payload содержит `[product_id, seller_id, json_after]`
- Событие `PRODUCT_EDITED`: payload содержит `[product_id, seller_id, json_before, json_after]`
- `event_type`: `PRODUCT_CREATED` / `PRODUCT_EDITED` (заглавными, без точки)
- `idempotency_key`: строго UUID
- `occurred_at`: datetime

## История исправлений по замечаниям AI-арбитра

### Итерация 1: Первоначальная реализация
- Endpoint `POST /api/v1/skus` (201 Created)
- Переход товара `DRAFT → ON_MODERATION` при первом SKU
- Outbox-паттерн для событий в Moderation
- Защита от добавления SKU к `HARD_BLOCKED` (403)
- Единый формат ошибок `{code, message}`
- Проверка владельца через `X-Seller-Id`

### Итерация 2: Исправления по контракту
- Добавлены поля `discount`, `cost_price`, `active_quantity`, `reserved_quantity`, `updated_at` в `SKUResponse`
- В `images` добавлены `id` и `ordering`, в `characteristics` — `id`
- Формат события в outbox: `event_type` → `PRODUCT_CREATED`/`PRODUCT_EDITED` (заглавными)
- Добавлено поле `occurred_at` в outbox
- `idempotency_key` → строго UUID
- Реализована re-moderation: `MODERATED`/`BLOCKED` → `ON_MODERATION`
- Аутентификация через `Authorization: Bearer`
- Обработка `IntegrityError` для дублирующегося артикула (409)
- Добавлено поле `status` в модель SKU

### Итерация 3: Финальные исправления (текущая)
- `DRAFT` → `CREATED` в соответствии со спецификацией `b2b/openapi.yaml`
- Добавлен `json_after` в outbox payload события `PRODUCT_CREATED`
- Добавлены `json_before` и `json_after` в outbox payload события `PRODUCT_EDITED`
- Восстановлен тест `first_sku_emits_created_event_to_moderation`
- Усилен тест `second_sku_no_state_change` (строгая проверка `len(events) == 0`)

## ADR-1: Outbox-паттерн для событий модерации

**Контекст:** При создании первого SKU необходимо отправить событие `PRODUCT_CREATED` в Moderation Service. Прямой HTTP-вызов создаёт риск потери события при падении сервиса.

**Рассмотренные альтернативы:**
1. Прямой HTTP-вызов. Просто в реализации, но при падении Moderation событие теряется.
2. Очередь сообщений (RabbitMQ/Kafka). Надёжно, но избыточно для MVP.
3. Outbox-паттерн. Запись события в БД в той же транзакции, что и бизнес-операция.

**Выбрано:** Outbox-паттерн (таблица `moderation_event_outbox`).

**Критерии выбора:**
- **Атомарность:** Бизнес-операция и событие либо фиксируются вместе, либо откатываются вместе
- **Надёжность:** Событие не потеряется при падении сервиса
- **Аудит:** Все отправленные события хранятся в БД

## ADR-2: Снимки состояния `json_before` / `json_after`

**Контекст:** Moderation Service должен видеть, как изменился товар, для принятия решения. В спецификации `moderation/openapi.yaml` событие `EventProductEdited` требует оба снимка.

**Выбранное решение:** В payload события `PRODUCT_EDITED` передаются оба снимка — до и после изменений. Для `PRODUCT_CREATED` передаётся только `json_after`.

**Критерии:**
- Полная информация об изменениях
- Возможность аудита и отката
- Соответствие контракту `moderation/openapi.yaml`

## ADR-3: Статус CREATED вместо DRAFT

**Контекст:** В спецификации `b2b/openapi.yaml` enum `ProductStatus` содержит только `[CREATED, ON_MODERATION, MODERATED, BLOCKED, HARD_BLOCKED]`. Значение `DRAFT` отсутствует.

**Выбранное решение:** Использовать `CREATED` как начальный статус товара.

**Критерии:**
- Соответствие спецификации
- Избежание ошибок при интеграции с реальным B2B-сервисом

## Лог тестов (DoD)
platform win32 -- Python 3.12.3, pytest-9.0.3, pluggy-1.6.0
collected 8 items
tests/test_sku_canonical_flow.py::test_first_sku_transitions_product_to_on_moderation PASSED
tests/test_sku_canonical_flow.py::test_first_sku_emits_created_event_to_moderation PASSED
tests/test_sku_canonical_flow.py::test_second_sku_no_state_change PASSED
tests/test_sku_canonical_flow.py::test_add_sku_to_hard_blocked_returns_403 PASSED
tests/test_sku_canonical_flow.py::test_add_sku_to_blocked_triggers_re_moderation PASSED
tests/test_sku_canonical_flow.py::test_missing_owner_returns_403 PASSED
tests/test_sku_canonical_flow.py::test_product_not_found_returns_404 PASSED
tests/test_sku_canonical_flow.py::test_duplicate_article_returns_409 PASSED
