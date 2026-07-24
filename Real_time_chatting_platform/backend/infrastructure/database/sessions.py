from sqlalchemy.ext.asyncio import AsyncSession, create_engine_session, async_sessionmaker as sessionmaker
from core.config import settings

engine = create_engine_session(
    settings.database_url,
    echo = settings.debug,
    pool_pre_ring = True
)

AsyncSessionLocal = sessionmaker(
    bind = engine,
    class_ = AsyncSession,
    expire_on_commit = False
)

async def get_db() -> AsyncSession:

    async with AsyncSessionLocal() as session:
        try:
            yield session

        except Exception as e:

            await session.rollback()
            raise
         
        finally:
            await session.close()
