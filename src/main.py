from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from src.api.v1.skus import router as skus_router
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

app = FastAPI(title="NeoMarket B2B Core - US-B2B-02")

app.add_exception_handler(AppError, app_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(Exception, global_exception_handler)

app.include_router(skus_router)