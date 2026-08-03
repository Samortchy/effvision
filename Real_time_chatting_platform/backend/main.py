from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from infrastructure.database.sessions import get_db, engine
from api.routes.messages import router as messages_router
from api.routes.notifications import router as notifications_router
from core.logger import configure_logging
from infrastructure.middleware import LoggingMiddleware

from api.routes.conversations import router as conversations_router
from api.routes.auth import router as auth_router
from api.routes.users import router as users_router

from infrastructure.database.sessions import AsyncSessionLocal
from infrastructure.repositories.conversation_repository_sqla import SQLAlchemyConversationRepository
from application.use_cases.conversations.ensure_public_conversation import EnsurePublicConversationUseCase

@asynccontextmanager
async def lifSpan(app: FastAPI):
    async with engine.begin() as conn:
        pass

    async with AsyncSessionLocal() as session:
        repo = SQLAlchemyConversationRepository(session)
        await EnsurePublicConversationUseCase(repo).execute()
        await session.commit()
        
    yield
    await engine.dispose()

configure_logging()
app = FastAPI(lifespan=lifSpan)

# The Vite dev server is a different origin from the API, so every browser call
# from it is cross-origin. Listed explicitly rather than "*": credentials are
# sent on these routes, and the wildcard is ignored once they are.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    # The frontend reads no custom headers today; X-Request-ID is exposed so a
    # failing request can be traced back to its log line.
    expose_headers=["X-Request-ID"],
)

app.add_middleware(LoggingMiddleware)

app.include_router(auth_router)
app.include_router(users_router)
app.include_router(conversations_router)
app.include_router(messages_router)
app.include_router(notifications_router)


@app.get("/health")
async def health_check(db :AsyncSession = Depends(get_db)):
    await db.execute(text("SELECT 1"))
    return {"status": "ok", "database": "ok"}