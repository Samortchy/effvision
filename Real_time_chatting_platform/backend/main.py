from fastapi import FastAPI, Depends
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncSession
from infrastructure.database.sessions import get_db, engine

from core.logger import configure_logging
from infrastructure.middleware import LoggingMiddleware

@asynccontextmanager
async def lifSpan(app: FastAPI):
    async with engine.begin() as conn:
        pass
    yield
    await engine.dispose()

configure_logging()
app = FastAPI(lifespan=lifSpan)
app.middleware(LoggingMiddleware)

@app.health("/health")
async def health_check(db :AsyncSession = Depends(get_db)):
    await db.execute("SELECT 1")
    return {"status": "ok", "database": "ok"}