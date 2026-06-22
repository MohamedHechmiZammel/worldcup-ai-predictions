import asyncio
from logging.config import fileConfig

from sqlalchemy import pool

from alembic import context

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Import all models so Alembic can detect them
from app.core.database import Base  # noqa: E402
from app.models import team, match, live_event, model_version, prediction, accuracy_record  # noqa: F401, E402

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    from app.core.config import settings
    context.configure(
        url=settings.database_url_clean,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    from sqlalchemy.ext.asyncio import create_async_engine
    from app.core.config import settings

    connectable = create_async_engine(
        settings.database_url_clean,
        poolclass=pool.NullPool,
        connect_args=settings.database_connect_args,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
