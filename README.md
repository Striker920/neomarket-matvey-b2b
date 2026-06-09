# Исправление Задания 1 (US-B2B-02): Соответствие контракту создания SKU


## Внесенные исправления:
1. **Полный ответ**: Endpoint теперь возвращает полный набор полей варианта (`stock_quantity`, `article`, `images`, `characteristics`, `created_at`, `status`), а не усеченный набор из 5 полей.
2. **Снятие лишних ограничений**: 
   - Поле `images` сделано опциональным (`default_factory=list`).
   - Цена `price` теперь допускает значение `0` (`ge=0` вместо `gt=0`).
3. **Единый формат ошибок**: Все ошибки теперь возвращаются в формате `{"code": "...", "message": "..."}` через кастомные exception handlers (вместо стандартного `{"detail": "..."}`).
4. **Статусы товара**: Значения Enum приведены к верхнему регистру (`DRAFT`, `ON_MODERATION`, `HARD_BLOCKED` и т.д.) в соответствии с контрактом.
5. **Проверка владельца**: Добавлена проверка `seller_id` из заголовка `X-Seller-Id`. Попытка создать SKU для чужого товара возвращает `403 FORBIDDEN`.
6. **Коды ответов**: Несуществующий товар теперь корректно возвращает `404 PRODUCT_NOT_FOUND` вместо `400`.

## ADR: Единый формат ошибок
Для соблюдения контракта внедрен глобальный обработчик исключений FastAPI. 
- Критерий 1: Совместимость с фронтендом/B2B-клиентами, ожидающими строго `{code, message}`.
- Критерий 2: Централизованная обработка без дублирования логики форматирования в каждом сервисе.

## Лог тестов (DoD для Задания 1)


s\Python\Python312\python.exe
cachedir: .pytest_cache
rootdir: C:\US-B2B-02
plugins: anyio-4.13.0
collected 6 items                                      

tests/test_sku_canonical_flow.py::test_first_sku_transitions_product_to_on_moderation PASSED [ 16%]
tests/test_sku_canonical_flow.py::test_first_sku_emits_created_event_to_moderation PASSED [ 33%]
tests/test_sku_canonical_flow.py::test_second_sku_no_state_change PASSED [ 50%]
tests/test_sku_canonical_flow.py::test_add_sku_to_hard_blocked_returns_403 PASSED [ 66%]
tests/test_sku_canonical_flow.py::test_missing_owner_returns_403 PASSED [ 83%]
tests/test_sku_canonical_flow.py::test_product_not_found_returns_404 PASSED [100%]

## Чек-лист замечаний арбитра
- [x] Ответ содержит полный набор полей варианта
- [x] Изображения опциональны, цена >= 0
- [x] Ошибки в формате {code, message}
- [x] Статусы в верхнем регистре (DRAFT, ON_MODERATION)
- [x] Проверка владельца (X-Seller-Id)
- [x] Несуществующий товар возвращает 404
