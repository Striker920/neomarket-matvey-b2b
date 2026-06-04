from fastapi import FastAPI
from src.models.base import Base
from src.models.order import Order, OrderItem
from src.database import engine
from src.api.v1.orders import router as orders_router

Base.metadata.create_all(bind=engine)

app = FastAPI(title="NeoMarket B2C Orders (Matvey)")
app.include_router(orders_router)