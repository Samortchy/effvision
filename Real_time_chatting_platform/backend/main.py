from fastapi import FastAPI, Depends
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncSession
from infrastructure.database.sessions import get_db, engine

@asynccontextmanager
async def lifSpan(app: FastAPI):
    async with engine.begin() as conn:
        pass
    yield
    await engine.dispose()

app = FastAPI(lifespan=lifSpan)

@app.health("/health")
async def health_check(db :AsyncSession = Depends(get_db)):
    await db.execute("SELECT 1")
    return {"status": "ok", "database": "ok"}