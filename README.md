# Исправление US-B2B-02: критический баг с autoflush при добавлении первого SKU

## Описание
Исправлен критический баг: в production-среде первый SKU не переводил товар в ON_MODERATION и не создавал outbox-событие PRODUCT_CREATED.

## Корень проблемы

**Два связанных бага:**

1. **Зависимость от autoflush:** В `src/services/sku_service.py` после `db.add(sku)` выполнялся повторный `db.query(func.count(SKU.id))`. В production-сессии `autoflush=False` (настройка `src/database.py:5`), поэтому новая SKU-запись невидима для COUNT — возвращается 0 вместо 1. Условие `if sku_count == 1` никогда не срабатывает.

2. **Отсутствие явного commit:** После изменения `product.status` вызывался только `db.flush()`, но не `db.commit()`. В тестовой сессии с `autoflush=True` изменения автоматически сохранялись при закрытии сессии — тесты проходили. В production с `autoflush=False` изменения статуса оставались в транзакции и терялись.

**Почему тесты маскировали баг:**
- Production-сессия: `sessionmaker(autocommit=False, autoflush=False, bind=engine)`
- Тестовая сессия: `sessionmaker(bind=engine)` — по умолчанию `autoflush=True`

Это расхождение создавало иллюзию корректной работы, хотя в production первый SKU никогда не запускал модерацию.

## Внесённые исправления

### 1. Устранение зависимости от autoflush (`src/services/sku_service.py`)
**Было:** повторный `COUNT` после `db.add(sku)`.
**Стало:** использование `sku_count_after = sku_count_before + 1` — количество SKU уже известно до добавления.

**Преимущества:**
- ✅ Нет зависимости от autoflush
- ✅ Убран лишний запрос к БД
- ✅ Код чище и быстрее

### 2. Явный commit (`src/services/sku_service.py`)
Добавлен `db.commit()` перед `return`, чтобы изменения статуса товара и outbox-события гарантированно сохранялись в БД независимо от настроек сессии.

### 3. Тестовая сессия с autoflush=False (`tests/test_sku_canonical_flow.py`)
Явно установлен `autoflush=False`, чтобы тесты воспроизводили production-поведение и не маскировали баги.

### 4. Детерминированный idempotency_key
Формат: `sku-{sku_id}-{product_id}-{event_type}`. Защищает от дублирования outbox-событий при retry.

### 5. Исправлен отступ
`json_before` добавляется только для `PRODUCT_EDITED`, а не для всех событий (был синтаксический баг).

## ADR: Обработка autoflush при подсчёте SKU

**Контекст:** При добавлении SKU нужно определить, является ли он первым (для перевода CREATED → ON_MODERATION + PRODUCT_CREATED). В production-сессии `autoflush=False`, поэтому новая запись невидима для COUNT.

**Рассмотренные альтернативы:**

1. **Явный `db.flush()` перед COUNT** — делает новую запись видимой. Надёжно, но добавляет лишний запрос к БД и создаёт неявную зависимость от flush.
2. **Использовать `sku_count_before + 1`** — количество SKU уже известно до добавления (оно равно 0 для первого SKU). Не требует дополнительного запроса.
3. **Включить autoflush в production** — опасно, может сломать другие части кода, которые полагаются на явный commit.

**Выбрано:** Вариант 2 — использовать `sku_count_before + 1`.

**Критерии выбора:**
- **Производительность:** Вариант 2 не делает лишний запрос к БД. Вариант 1 добавляет flush + COUNT.
- **Надёжность:** Вариант 2 не зависит от настроек сессии. Вариант 1 работает, но создаёт неявную зависимость от flush.

**Дополнительно:** Явный `db.commit()` гарантирует сохранение изменений независимо от настроек сессии.

## Лог тестов (DoD)
======================================= test session starts ========================================
platform win32 -- Python 3.12.3, pytest-9.0.3, pluggy-1.6.0 -- C:\Users\matvey_chertovikov\AppData\Local\Programs\Python\Python312\python.exe
cachedir: .pytest_cache
rootdir: C:\US-B2B-02
plugins: anyio-4.13.0
collected 8 items                                                                                   

tests/test_sku_canonical_flow.py::test_first_sku_transitions_product_to_on_moderation PASSED  [ 12%]
tests/test_sku_canonical_flow.py::test_first_sku_emits_created_event_to_moderation PASSED     [ 25%]
tests/test_sku_canonical_flow.py::test_second_sku_no_state_change PASSED                      [ 37%]
tests/test_sku_canonical_flow.py::test_add_sku_to_blocked_triggers_re_moderation PASSED       [ 62%]

========================================= warnings summary ========================
