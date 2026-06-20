# Исправление US-B2B-10: форма ответа fulfill

## Описание
Реализованы финальные исправления для полного соответствия спецификации `b2b/openapi.yaml`.

## Внесённые исправления

### 1. Форма ответа fulfill (`src/services/fulfill_service.py`)
**Было:** `{"ok": True}`
**Стало:** `{"order_id": "...", "status": "FULFILLED", "processed_at": "..."}` согласно `b2b/openapi.yaml:1735-1741`

### 2. Формат timestamp
`processed_at` в формате ISO 8601 с суффиксом `Z` (UTC).

### 3. Идемпотентность
`FulfillOperation` сохраняет новую форму ответа, поэтому повторный вызов возвращает тот же `InventoryOrderResponse`.

### 4. Обновлены тесты (`tests/test_fulfill.py`)
- `test_fulfill_decreases_reserved_quantity` — проверяет `order_id`, `status == "FULFILLED"`, `processed_at`
- `test_active_quantity_unchanged` — проверяет новую форму ответа
- `test_idempotent_fulfill_no_double_deduction` — проверяет совпадение ответов при повторном вызове

## ADR: Формат timestamp в ответе

**Контекст:** `processed_at` должен быть в формате ISO 8601.

**Выбрано:** `datetime.utcnow().isoformat() + "Z"` — UTC время с суффиксом Z.

**Критерии:**
- **Соответствие спецификации:** ISO 8601 с явным указанием UTC
- **Совместимость:** Стандартный формат для API

## Лог тестов (DoD)
platform win32 -- Python 3.12.3, pytest-9.0.3, pluggy-1.6.0 -- C:\Users\matvey_chertovikov\AppData\Local\Programs\Python\Python312\python.exe
cachedir: .pytest_cache
rootdir: C:\neomarket-matvey-b2b-10-12-test-fulfill-endpoint
plugins: anyio-4.13.0
collected 6 items                                                                      

tests/test_fulfill.py::TestFulfill::test_fulfill_decreases_reserved_quantity PASSED [ 16%]
tests/test_fulfill.py::TestFulfill::test_active_quantity_unchanged PASSED        [ 33%]
tests/test_fulfill.py::TestFulfill::test_idempotent_fulfill_no_double_deduction PASSED [ 50%]
tests/test_fulfill.py::TestFulfill::test_missing_service_key_returns_401 PASSED  [ 66%]
tests/test_fulfill.py::TestFulfill::test_sku_not_found_returns_404 PASSED        [ 83%]
tests/test_fulfill.py::TestFulfill::test_insufficient_reservation_returns_409 PASSED [100%]

