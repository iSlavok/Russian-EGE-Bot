from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from loguru import logger
from sqlalchemy import URL
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import database_settings

database_url = URL.create(
    drivername="postgresql+asyncpg",
    host=database_settings.HOST,
    port=database_settings.PORT,
    username=database_settings.USER,
    password=database_settings.PASS.get_secret_value(),
    database=database_settings.NAME,
)

async_engine = create_async_engine(
    database_url,
    echo=False,
    future=True,
    pool_size=database_settings.POOL_SIZE,
    pool_pre_ping=True,
)

async_session_factory = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession]:
    async with async_session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def close_db() -> None:
    await async_engine.dispose()
    logger.success("Database connection closed successfully")
