# fix(us-b2b-04): приведение DELETE /products/{id} к спецификации OpenAPI (204 No Content)

## 🎯 Цель

Исправить замечание арбитра по задаче **US-B2B-04**: endpoint `DELETE /api/v1/products/{id}` возвращал `200 OK` с телом `{"ok": true}`, что расходилось со спецификацией `b2b/openapi.yaml` (операция `deleteProduct`, ответ `204`).

## 🔍 Контекст (фидбэк арбитра)

> `DELETE /api/v1/products/{id}` возвращает `200` с телом `{"ok": true}` вместо `204 No Content` по спецификации `b2b/openapi.yaml`. Тест `test_delete_sets_deleted_true` фиксирует статус `200` — тест закрепляет поведение, расходящееся со спецификацией, и сломается при правильной реализации.

## ✅ Что сделано

### `src/api/products.py`
- Добавлен импорт `Response` из `fastapi`
- У endpoint `delete_product` добавлены параметры `status_code=204, response_class=Response`
- Вместо `return {"ok": True}` теперь `return Response(status_code=204)` — без тела ответа

```python
@router.delete("/{product_id}", status_code=204, response_class=Response)
def delete_product(
    product_id: UUID,
    seller_id: UUID = Depends(get_current_seller_id),
    db: Session = Depends(get_db)
):
    service = ProductService(db)
    service.delete_product(product_id=str(product_id), seller_id=str(seller_id))
    return Response(status_code=204)
