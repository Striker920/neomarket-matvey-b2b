from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError

from app.api.v1 import products
from app.core.database import Base, engine
from app.errors import ApiError, api_error_handler, validation_error_handler

# Создаем таблицы
Base.metadata.create_all(bind=engine)

app = FastAPI(title="B2B Service", version="1.0.0")

# ✅ Глобальные exception handlers
app.add_exception_handler(ApiError, api_error_handler)
app.add_exception_handler(RequestValidationError, validation_error_handler)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключаем роутеры
app.include_router(products.router, prefix="/api/v1/products", tags=["products"])

@app.get("/health")
async def health_check():
    return {"status": "ok"}