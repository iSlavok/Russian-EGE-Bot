# noqa: INP001
import asyncio
from logging.config import fileConfig

from alembic import context
from loguru import logger
from sqlalchemy.engine.base import Connection

from app.database import BaseDBModel, async_engine  # type: ignore[missing-import]
from app.models import *  # noqa: F403  # type: ignore[missing-import]

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = BaseDBModel.metadata


def run_migrations_offline() -> None:
    logger.warning("Running migrations in offline mode is not supported in this setup.")


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    connectable = async_engine

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
