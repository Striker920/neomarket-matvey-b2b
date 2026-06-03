from fastapi import FastAPI
from src.api.v1.skus import router as skus_router
from src.api.v1.moderation_events import router as moderation_router
from src.api.v1.products import router as products_router
from src.models.base import Base
from src.database import engine

Base.metadata.create_all(bind=engine)

app = FastAPI(title="NeoMarket B2B Core (Matvey)")
app.include_router(skus_router)
app.include_router(moderation_router)
app.include_router(products_router)