"""
Alembic environment script.

Customized from the stock template to:
  1. Pull the DB URL from our own pydantic-settings config (.env-driven)
     instead of a hardcoded value in alembic.ini.
  2. Point at our SQLAlchemy Base.metadata so `alembic revision
     --autogenerate` can diff the real models against the live schema.
"""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from src.config import settings
from src.db.models import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Use the sync DB URL (psycopg2) — Alembic's migration runner is
# synchronous, even though the app itself uses the async driver.
config.set_main_option("sqlalchemy.url", settings.database_url_sync)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Generate SQL scripts without a live DB connection (rarely used
    here, but kept for completeness / CI dry-runs)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Connect to the real DB and apply migrations directly — this is
    the path `alembic upgrade head` takes."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
