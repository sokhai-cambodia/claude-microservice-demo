from contextlib import asynccontextmanager
from fastapi import FastAPI
from .database import engine, Base
from .models import Order, OrderItem  # must be imported before create_all
from .routes.orders import router as orders_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(title="order-service", version="1.0.0", lifespan=lifespan)
app.include_router(orders_router, prefix="/orders", tags=["orders"])
