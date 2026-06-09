from contextlib import asynccontextmanager
from fastapi import FastAPI
from .database import engine, Base
from .models import User  # must be imported before create_all
from .routes.auth import router as auth_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(title="auth-service", version="1.0.0", lifespan=lifespan)
app.include_router(auth_router, prefix="/auth", tags=["auth"])
