from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker as sessionmaker
from core.config import settings

engine = create_async_engine(
    settings.database_url,
    echo = settings.debug,
    pool_pre_ping = True
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
            await session.commit()
            
        except Exception as e:

            await session.rollback()
            raise

        finally:
            await session.close()
