# fix(us-b2b-07): каталог товаров для B2C (service-to-service)

## 🎯 Цель

Реализовать режим каталога в B2B-сервисе — `GET /api/v1/public/products` для межсервисных вызовов от B2C с IDOR-защитой и фильтрами видимости.

## 🔍 Контекст

Покупатель открывает витрину — B2C запрашивает у B2B список товаров. Это не запрос продавца, это межсервисный вызов. Если B2B вернёт `cost_price` или `reserved_quantity`, чувствительные данные продавца утекут в B2C — это IDOR-уязвимость.

## 🔧 Исправления по фидбэку арбитров

### Проблема
1. Отсутствовали обязательные поля: `slug`, `seller_id`, `category_id`, `min_price`, `created_at`
2. Поле `category` возвращалось как вложенный объект вместо скалярного `category_id: UUID`
3. Query-параметр `category` вместо `category_id`

### Решение

| Было | Стало |
|------|-------|
| `ProductCatalogItem` без `slug`, `seller_id`, `category_id`, `min_price`, `created_at` | ✅ Все поля добавлены |
| `category: {id, name}` (вложенный объект) | ✅ `category_id: UUID` (скалярный) |
| Query-параметр `?category=...` | ✅ `?category_id=...` |

## ✅ Что реализовано

### Endpoint
`GET /api/v1/public/products`

### Авторизация
- Заголовок: `X-Service-Key` (межсервисный, не JWT продавца)
- Без заголовка или неверный ключ → **401 Unauthorized**

### Фильтры видимости
- ✅ Только `status = MODERATED`
- ✅ Только `deleted = False`
- ✅ Только товары с `active_quantity > 0`
- ✅ Исключены `HARD_BLOCKED`

### Query-параметры
- `limit`, `offset` — пагинация
- `search` — поиск по title/description
- `category_id` — фильтр по категории
- `sort` — сортировка (price_asc, price_desc, date_desc)
- `ids` — batch-запрос (только видимые из списка)

### IDOR-защита
- ❌ НЕ возвращает `cost_price`
- ❌ НЕ возвращает `reserved_quantity`
- ✅ Возвращает только публичные поля

### Response (ProductCatalogItem)
```json
{
  "id": "uuid",
  "title": "iPhone 15",
  "slug": "iphone-15",
  "seller_id": "uuid",
  "category_id": "uuid",
  "min_price": 100000,
  "has_stock": true,
  "images": ["/s3/front.jpg"],
  "created_at": "2026-06-22T10:00:00Z"
}
Лог тестов
platform win32 -- Python 3.12.3, pytest-7.4.3, pluggy-1.6.0 -- C:\Users\matvey_chertovikov\AppData\Local\Programs\Python\Python312\python.exe
cachedir: .pytest_cache
rootdir: C:\neomarket-matvey-b2b-feature-us-b2b-07-catalog
plugins: anyio-3.7.1, asyncio-0.21.1
asyncio: mode=Mode.STRICT
collected 6 items                                                                                               

tests/test_b2c_catalog.py::TestB2CCatalog::test_catalog_returns_moderated_in_stock_products PASSED        [ 16%]
tests/test_b2c_catalog.py::TestB2CCatalog::test_catalog_excludes_hard_blocked PASSED                      [ 33%]
tests/test_b2c_catalog.py::TestB2CCatalog::test_catalog_missing_service_key_returns_401 PASSED            [ 50%]
tests/test_b2c_catalog.py::TestB2CCatalog::test_catalog_response_has_no_cost_price PASSED                 [ 66%]
tests/test_b2c_catalog.py::TestB2CCatalog::test_batch_ids_returns_visible_subset PASSED                   [ 83%]
tests/test_b2c_catalog.py::TestB2CCatalog::test_filter_by_category_id PASSED                              [100%]
