# Исправление US-B2B-02 по замечаниям AI-арбитра (финальная версия)

## Описание
Реализованы все исправления для полного соответствия контракту API создания SKU.

## Внесенные исправления

### 1. Полный контракт ответа SKUResponse
Добавлены все обязательные поля:
- `discount` (скидка в копейках)
- `cost_price` (себестоимость, nullable)
- `active_quantity` (сток минус зарезервированное)
- `reserved_quantity` (зарезервировано)
- `updated_at` (datetime)

В массиве `images` каждый элемент теперь содержит `id`, `url`, `ordering`.
В массиве `characteristics` каждый элемент теперь содержит `id`, `name`, `value`.

### 2. Формат события в outbox соответствует контракту Moderation
- `event_type` → `"PRODUCT_CREATED"` или `"PRODUCT_EDITED"` (заглавными, без точки)
- добавлено поле `occurred_at` (datetime)
- в `payload` добавлено обязательное поле `json_after` (снимок состояния товара)
- `idempotency_key` → строго UUID (через `str(uuid.uuid4())`)

### 3. Реализована повторная модерация
- Добавление SKU к товару в статусе `MODERATED` или `BLOCKED` переводит его в `ON_MODERATION` и отправляет событие `PRODUCT_EDITED`.
- Товар в `BLOCKED` теперь уходит на повторную модерацию, а не отклоняется с 400.

### 4. Аутентификация через Bearer токен
Реализована функция `get_current_seller`, которая читает заголовок `Authorization: Bearer <token>`. В реальной системе здесь будет парсинг JWT.

### 5. Обработка IntegrityError для article
Добавлен перехват `IntegrityError` при попытке создать SKU с дублирующимся артикулом. Возвращается 409 с кодом `ARTICLE_ALREADY_EXISTS`.

### 6. Добавлено поле status в модель SKU
В модель `SKU` добавлено поле `status` (enum: `ACTIVE`, `INACTIVE`, `OUT_OF_STOCK`), которое отсутствовало в предыдущей версии.

## Лог тестов (DoD)

platform win32 -- Python 3.12.3, pytest-9.0.3, pluggy-1.6.0 -- C:\Users\matvey_chertovikov\AppData\Local\Programs\Python\Python312\python.exe
cachedir: .pytest_cache
rootdir: C:\US-B2B-02
plugins: anyio-4.13.0
collected 7 items                                                                                    

tests/test_sku_canonical_flow.py::test_first_sku_transitions_product_to_on_moderation PASSED   [ 14%]
tests/test_sku_canonical_flow.py::test_second_sku_no_state_change PASSED                       [ 28%]
tests/test_sku_canonical_flow.py::test_add_sku_to_hard_blocked_returns_403 PASSED              [ 42%]
tests/test_sku_canonical_flow.py::test_add_sku_to_blocked_triggers_re_moderation PASSED        [ 57%]
tests/test_sku_canonical_flow.py::test_missing_owner_returns_403 PASSED                        [ 71%]
tests/test_sku_canonical_flow.py::test_product_not_found_returns_404 PASSED                    [ 85%]
tests/test_sku_canonical_flow.py::test_duplicate_article_returns_409 PASSED                    [100%]

## Чек-лист замечаний арбитра
- [x] SKUResponse содержит все обязательные поля (discount, cost_price, active_quantity, reserved_quantity, updated_at)
- [x] images содержит id, url, ordering
- [x] characteristics содержит id, name, value
- [x] Outbox event shape соответствует контракту (PRODUCT_CREATED/EDITED, occurred_at, json_after, UUID idempotency_key)
- [x] Реализована повторная модерация (MODERATED/BLOCKED → ON_MODERATION + PRODUCT_EDITED)
- [x] Аутентификация через Bearer токен
- [x] Обработка IntegrityError для article (409 ARTICLE_ALREADY_EXISTS)
- [x] Все 7 тестов проходят
