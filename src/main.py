from fastapi import FastAPI
from src.api.v1.skus import router as skus_router
from src.models.base import Base
from src.database import engine

# Создание таблиц (для упрощения, в проде используйте Alembic)
Base.metadata.create_all(bind=engine)

app = FastAPI(title="NeoMarket B2B Core (Matvey)")
app.include_router(skus_router)