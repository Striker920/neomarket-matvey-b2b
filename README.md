# Реализация US-B2B-09: применение решения модерации к товару

## Описание
Реализован endpoint POST /api/v1/moderation/events для обработки вердиктов от Moderation Service. Реализация строго соответствует спецификации neomarket-protocols/b2b/openapi.yaml. 

Поддерживаются сценарии:
- MODERATED: товар одобрен, данные блокировки очищаются.
- BLOCKED: товар заблокирован (мягкая или жесткая блокировка в зависимости от флага hard_block).

Реализован каскад событий PRODUCT_BLOCKED в B2C через Outbox и защита от дублирования входящих событий через Inbox pattern.

## ADR: Гарантия идемпотентности входящих событий

Контекст: События от Moderation могут быть доставлены дважды из-за сетевых сбоев или механизмов повторной отправки. Необходимо гарантировать отсутствие побочных эффектов при повторной обработке.

Рассмотренные альтернативы:
1. Поле last_event_key в модели Product. Просто в реализации, но не масштабируется на разные типы событий и уязвимо к race-condition при параллельной обработке.
2. Upsert с условием в БД. Сложно реализуемо в SQLAlchemy, зависит от конкретного диалекта СУБД (например, PostgreSQL specific), что усложняет поддержку.
3. Таблица processed_events (Inbox pattern). Отдельная таблица с первичным ключом по составному полю (sender_service, idempotency_key).

Выбрано: Таблица processed_events (Inbox pattern).

Критерии выбора:
- Риск race-condition: Уникальное ограничение (Primary Key) на уровне базы данных гарантирует, что параллельные запросы с одинаковым idempotency_key не будут обработаны дважды (второй запрос завершится ошибкой IntegrityError, которая перехватывается).
- Сложность поддержки: Решение полностью отделено от бизнес-модели Product. Это позволяет легко аудировать историю полученных событий и настраивать автоматическую очистку старых записей по TTL (24 часа).

## Лог тестов (DoD)

platform win32 -- Python 3.12.3, pytest-9.0.3, pluggy-1.6.0 -- C:\Users\matvey_chertovikov\AppData\Local\Programs\Python\Python312\python.exe
cachedir: .pytest_cache
rootdir: C:\US-B2B-09
plugins: anyio-4.13.0
collected 6 items                                                                                                  

tests/test_moderation_flow.py::test_moderated_event_clears_blocking_data PASSED                              [ 16%]
tests/test_moderation_flow.py::test_blocked_soft_saves_field_reports PASSED                                  [ 33%]
tests/test_moderation_flow.py::test_blocked_hard_sets_terminal_status PASSED                                 [ 50%]
tests/test_moderation_flow.py::test_hard_blocked_product_rejects_seller_edits PASSED                         [ 66%]
tests/test_moderation_flow.py::test_duplicate_event_same_idempotency_key_no_side_effects PASSED              [ 83%]
tests/test_moderation_flow.py::test_missing_service_key_returns_401 PASSED   



platform win32 -- Python 3.12.3, pytest-9.0.3, pluggy-1.6.0 -- C:\Users\matvey_chertovikov\AppData\Local\Programs\Python\Python312\python.exe
cachedir: .pytest_cache
rootdir: C:\US-B2B-09
plugins: anyio-4.13.0
collected 5 items                                                                                                  

tests/test_sku_canonical_flow.py::test_first_sku_transitions_product_to_on_moderation PASSED                 [ 20%]
tests/test_sku_canonical_flow.py::test_first_sku_emits_created_event_to_moderation PASSED                    [ 40%]
tests/test_sku_canonical_flow.py::test_second_sku_no_state_change PASSED                                     [ 60%]
tests/test_sku_canonical_flow.py::test_add_sku_to_hard_blocked_returns_403 PASSED                            [ 80%]
tests/test_sku_canonical_flow.py::test_missing_image_returns_400 PASSED  
