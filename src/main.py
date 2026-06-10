from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from src.api.v1.moderation_events import router as moderation_router
from src.api.v1.products import router as products_router
from src.models.base import Base
from src.database import engine
from src.core.exceptions import (
    AppError,
    app_exception_handler,
    validation_exception_handler,
    http_exception_handler,
    global_exception_handler
)

Base.metadata.create_all(bind=engine)

app = FastAPI(title="NeoMarket B2B Core - US-B2B-09")

# Регистрация обработчиков исключений
app.add_exception_handler(AppError, app_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(Exception, global_exception_handler)

app.include_router(moderation_router)
app.include_router(products_router)