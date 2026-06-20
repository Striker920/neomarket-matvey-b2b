# feat(us-b2b-07): публичный каталог для B2C (service-to-service)

## 🎯 Цель

Реализовать публичный каталог товаров для B2C-сервиса (межсервисный вызов) с корректной авторизацией, фильтрами видимости и защитой от IDOR-утечки чувствительных полей.

## 🔍 Контекст (исправление по фидбэку арбитра)

Первая итерация прошла проверку, но были выявлены два несоответствия спецификации:

> 1. Публичный каталог реализован на `GET /api/v1/products`, тогда как спецификация `b2b/openapi.yaml` задаёт отдельный путь `GET /api/v1/public/products` (операция `listPublicProducts`, строка 728).
> 2. Исходящее событие `SKU_OUT_OF_STOCK` отправляется на `/api/v1/events`, тогда как спецификация `b2c/openapi.yaml` задаёт путь `/api/v1/b2b/events` — вызов уходил на несуществующий путь (404 в проде).

В этой итерации оба замечания устранены.

## ✅ Что сделано

### 1. Вынос B2C-каталога на отдельный роутер
- Создан новый роутер `src/api/public_products.py` с префиксом `/api/v1/public`
- Endpoint `GET /api/v1/public/products` — только для B2C (по `X-Service-Key`)
- Endpoint `GET /api/v1/products` оставлен **только для режима продавца** (JWT)
- Убран совмещённый режим из `GET /api/v1/products`

### 2. Исправлен путь события `SKU_OUT_OF_STOCK`
- Было: `{B2C_SERVICE_URL}/api/v1/events`
- Стало: `{B2C_SERVICE_URL}/api/v1/b2b/events` (согласно `b2c/openapi.yaml`)

### 3. Реализованы фильтры видимости
- Только `status = MODERATED`
- Только `deleted = false`
- Только `active_quantity > 0`
- Исключены `HARD_BLOCKED` товары

### 4. IDOR-защита
- В ответе каталога **нет** полей `cost_price` и `reserved_quantity`
- Проверка работает как для корня товара, так и для каждого SKU

### 5. Batch-запрос через `?ids=`
- Возвращает только видимые товары из списка
- Скрытые товары не вызывают 404 — просто не включаются в ответ

### 6. Авторизация через `X-Service-Key`
- Значение из env (`settings.B2C_SERVICE_KEY`)
- Без заголовка → `401 UNAUTHORIZED`
- С невалидным ключом → `401 UNAUTHORIZED`

## 📂 Изменения в файлах

### `src/api/public_products.py` (НОВЫЙ)
- Отдельный роутер для публичного каталога
- Функция `_require_b2c_service_key()` — проверка заголовка
- Endpoint `GET /api/v1/public/products` с фильтрами и batch-запросом

### `src/api/products.py`
- Убрана проверка `X-Service-Key` и B2C-логика из `GET /api/v1/products`
- Endpoint работает **только** в режиме продавца (JWT)
- Упрощена функция `get_products()` — только JWT-авторизация

### `src/services/event_service.py`
- Исправлен путь в `send_event_to_b2c()`: `/api/v1/events` → `/api/v1/b2b/events`
- Остальные события (`PRODUCT_DELETED`, `PRODUCT_EDITED`) уже шли на корректные пути

### `src/main.py`
- Подключён новый роутер `public_products.router`
- Порядок роутеров: `products` → `public_products` → остальные

### `tests/test_b2c_catalog.py`
- Все 5 тестов переведены на URL `/api/v1/public/products`
- Добавлены проверки для `active_quantity = 0` (товар не виден)

## 🧪 Тестовое покрытие

| # | Тест | Статус | Описание |
|---|------|:------:|----------|
| 1 | `test_catalog_returns_moderated_in_stock_products` | ✅ | Только MODERATED + deleted=false + active_quantity>0 |
| 2 | `test_catalog_excludes_hard_blocked` | ✅ | HARD_BLOCKED не попадает в выдачу |
| 3 | `test_catalog_missing_service_key_returns_401` | ✅ | Без X-Service-Key → 401 |
| 4 | `test_catalog_response_has_no_cost_price` | ✅ | В ответе нет cost_price и reserved_quantity |
| 5 | `test_batch_ids_returns_visible_subset` | ✅ | `?ids=` возвращает только видимые, без 404 для скрытых |

**Результат:** `5 passed` ✅

Запуск тестов:
platform win32 -- Python 3.12.3, pytest-9.0.3, pluggy-1.6.0 -- C:\Users\matvey_chertovikov\AppData\Local\Programs\Python\Python312\python.exe
cachedir: .pytest_cache
rootdir: C:\-US-B2B-03-main
plugins: anyio-4.13.0
collected 5 items                                                                                          

tests/test_b2c_catalog.py::TestB2CCatalog::test_catalog_returns_moderated_in_stock_products PASSED   [ 20%]
tests/test_b2c_catalog.py::TestB2CCatalog::test_catalog_excludes_hard_blocked PASSED                 [ 40%]
tests/test_b2c_catalog.py::TestB2CCatalog::test_catalog_missing_service_key_returns_401 PASSED       [ 60%]
tests/test_b2c_catalog.py::TestB2CCatalog::test_catalog_response_has_no_cost_price PASSED            [ 80%]
tests/test_b2c_catalog.py::TestB2CCatalog::test_batch_ids_returns_visible_subset PASSED              [100%]
