from contextlib import asynccontextmanager
from fastapi import FastAPI
from .database import engine, Base
from .models import Product  # must be imported before create_all
from .routes.products import router as products_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(title="product-service", version="1.0.0", lifespan=lifespan)
app.include_router(products_router, prefix="/products", tags=["products"])
