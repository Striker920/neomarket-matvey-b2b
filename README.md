# Исправление US-B2B-09 по замечаниям AI-арбитра

## Внесенные исправления

### 1. Единый формат ошибок {code, message}
Внедрён глобальный обработчик `http_exception_handler` в `src/core/exceptions.py`, который перехватывает все `HTTPException` (401, 403, 404, 500 и др.) и возвращает строгий формат `{"code": "...", "message": "..."}`.

- 401 → `{"code": "UNAUTHORIZED", "message": "Отсутствует или неверный ключ сервиса"}`
- 403 → `{"code": "FORBIDDEN", "message": "Доступ запрещен"}`
- 404 → `{"code": "NOT_FOUND", "message": "Ресурс не найден"}`
- 500 → `{"code": "INTERNAL_ERROR", "message": "Внутренняя ошибка сервера"}`

Защита от утечки внутренних деталей: убран `str(e)` из тела ответов.

### 2. Исправление схемы FieldReport
Поле `issue` в модели `FieldReport` переименовано в `comment` в соответствии с контрактом `neomarket-protocols`. Теперь реальные события модерации успешно парсятся.

### 3. Воркер отправки каскадных событий в B2C
Реализован `src/services/b2c_dispatcher.py`, который:
- Вычитывает события со статусом `pending` из таблицы `b2c_cascade_outbox`
- Отправляет их в B2C сервис
- Обновляет статус на `sent` (или `failed` при ошибке)

Воркер запускается асинхронно через `BackgroundTasks` после успешной обработки события модерации.

### 4. Модель Outbox
В `B2CCascadeOutbox` добавлено поле `status` для отслеживания состояния доставки (`pending`, `sent`, `failed`).

## ADR: Формат ошибок и обработка каскада

**Контекст:** Контракт требует единый формат ошибок `{code, message}` на верхнем уровне и реальную доставку каскадных событий в B2C.

**Выбранные решения:**
1. **Единый формат ошибок**: Глобальные exception handlers в FastAPI. Критерии: централизация логики, невозможность забыть формат в отдельных endpoint'ах, защита от утечки внутренних деталей.
2. **Воркер B2C**: BackgroundTasks + Outbox pattern. Критерии: гарантированная доставка (событие не теряется при падении), асинхронность (не блокирует ответ клиенту), отслеживание статуса доставки.

## Лог тестов (DoD)

platform win32 -- Python 3.12.3, pytest-9.0.3, pluggy-1.6.0 -- C:\Users\matvey_chertovikov\AppData\Local\Programs\Python\Python312\python.exe
cachedir: .pytest_cache
rootdir: C:\US-B2B-09
plugins: anyio-4.13.0
collected 6 items                                                        

tests/test_moderation_flow.py::test_moderated_event_clears_blocking_data PASSED [ 16%]
tests/test_moderation_flow.py::test_blocked_soft_saves_field_reports PASSED [ 33%]
tests/test_moderation_flow.py::test_blocked_hard_sets_terminal_status PASSED [ 50%]
tests/test_moderation_flow.py::test_hard_blocked_product_rejects_seller_edits PASSED [ 66%]
tests/test_moderation_flow.py::test_duplicate_event_same_idempotency_key_no_side_effects PASSED [ 83%]
tests/test_moderation_flow.py::test_missing_service_key_returns_401 PASSED [100%]

=========================== warnings summary ============================

## Чек-лист замечаний арбитра
- [x] Единый формат ошибок {code, message} на верхнем уровне
- [x] Поле `issue` переименовано в `comment` в FieldReport
- [x] Реальный воркер отправки каскадных событий в B2C (b2c_dispatcher)
- [x] Защита от утечки внутренних деталей (убран str(e))
- [x] Все 6 тестов проходят
