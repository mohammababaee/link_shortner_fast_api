from logging.config import fileConfig
from sqlalchemy import create_engine, pool
from alembic import context

# ⚠️ Import models BEFORE getting metadata
from app.db.models import BaseModel, ShortURL
from app.core.setting import settings

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ⚠️ Use BaseModel.metadata (or SQLModel.metadata)
from sqlmodel import SQLModel
target_metadata = SQLModel.metadata

def run_migrations_offline():
    sync_url = settings.DATABASE_URL.replace("+asyncpg", "")
    context.configure(
        url=sync_url,
        target_metadata=target_metadata,
        literal_binds=True
    )
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    sync_url = settings.DATABASE_URL.replace("+asyncpg", "")
    connectable = create_engine(sync_url, poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata
        )
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()