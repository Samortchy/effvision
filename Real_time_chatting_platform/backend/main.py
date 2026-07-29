from fastapi import FastAPI, Depends
from contextlib import asynccontextmanager
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from infrastructure.database.sessions import get_db, engine
from api.routes.messages import router as messages_router

from core.logger import configure_logging
from infrastructure.middleware import LoggingMiddleware

from api.routes.conversations import router as conversations_router
from api.routes.auth import router as auth_router
from api.routes.users import router as users_router
@asynccontextmanager
async def lifSpan(app: FastAPI):
    async with engine.begin() as conn:
        pass
    yield
    await engine.dispose()

configure_logging()
app = FastAPI(lifespan=lifSpan)
app.add_middleware(LoggingMiddleware)

app.include_router(auth_router)
app.include_router(users_router)
app.include_router(conversations_router)
app.include_router(messages_router)

@app.get("/health")
async def health_check(db :AsyncSession = Depends(get_db)):
    await db.execute(text("SELECT 1"))
    return {"status": "ok", "database": "ok"}