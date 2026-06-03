## Описание
Реализован канонический flow создания SKU (POST /api/v1/skus).
При добавлении первого SKU с ценой и фото товар переходит в статус ON_MODERATION, и событие product.created сохраняется в Outbox для отправки в Moderation Service.

## ADR: Доставка события CREATED в Moderation

Контекст: Необходимо уведомить Moderation о создании первого SKU, обеспечив устойчивость к сбоям сети.

Рассмотренные альтернативы:
1. Синхронный HTTP POST. Просто в реализации, но при недоступности Moderation транзакция B2B может откатиться или пользователь получит 500.
2. Fire-and-forget (асинхронный вызов без ожидания). Минимальная задержка ответа, но события теряются при сбоях, нет гарантий доставки.
3. Outbox Pattern (выбрано). Запись события в таблицу moderation_event_outbox в той же транзакции БД, что и создание SKU. Фоновый воркер отправляет запросы с заголовками X-Service-Key и Idempotency-Key.

Критерии выбора:
- Устойчивость к недоступности Moderation: если сервис недоступен, событие не теряется, а ретраится воркером по экспоненциальному бэкоффу.
- Консистентность данных: атомарность транзакции гарантирует, что статус ON_MODERATION и факт постановки события в очередь всегда согласованы.

## Лог тестов (DoD)

platform win32 -- Python 3.12.3, pytest-9.0.3, pluggy-1.6.0 -- C:\Users\matvey_chertovikov\AppData\Local\Programs\Python\Python312\python.exe
cachedir: .pytest_cache
rootdir: C:\US-B2B-02
plugins: anyio-4.13.0
collected 5 items                                                                                                  

tests/test_sku_canonical_flow.py::test_first_sku_transitions_product_to_on_moderation PASSED                 [ 20%]
tests/test_sku_canonical_flow.py::test_first_sku_emits_created_event_to_moderation PASSED                    [ 40%]
tests/test_sku_canonical_flow.py::test_second_sku_no_state_change PASSED                                     [ 60%]
tests/test_sku_canonical_flow.py::test_add_sku_to_hard_blocked_returns_403 PASSED                            [ 80%]
tests/test_sku_canonical_flow.py::test_missing_image_returns_400 PASSED                                      [100%]


## Чек-лист DoD
- first_sku_transitions_product_to_on_moderation: PASSED
- first_sku_emits_created_event_to_moderation: PASSED
- second_sku_no_state_change: PASSED
- add_sku_to_hard_blocked_returns_403: PASSED
- missing_image_returns_400 (422 Unprocessable Entity): PASSED
- ADR добавлен в описание PR
- Событие содержит idempotency_key и готовится к отправке с X-Service-Key
- Второй и последующие SKU добавляются без изменения статуса товара и без отправки события
