from __future__ import annotations

import sys
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import engine_from_config, pool

from alembic import context

# This is the Alembic Config object, which provides access to the
# values within the .ini file in use.
config = context.config

# Ensure project root is on sys.path so `app.*` imports work
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
from app.models.user import Base as UserBase  # noqa
from app.models.event import Base as EventBase  # noqa
from app.models.addons import Base as AddonsBase  # noqa

# If these Bases are distinct, choose one and reflect metadata; here they share same Base
from app.models.user import Base as target_metadata  # noqa

# build URL from env or settings
try:
    from app.core.settings import settings

    server = settings.DB_SERVER
    database = settings.DB_NAME
    username = settings.DB_USER
    password = settings.DB_PASSWORD
    driver = settings.DB_DRIVER
    port = settings.DB_PORT
    if any(sep in (server or "") for sep in (":", ",", "\\")):
        hostpart = server
    else:
        hostpart = f"{server}:{port}"
    driver_q = driver.replace(" ", "+")
    sqlalchemy_url = (
        f"mssql+pyodbc://{username}:{password}@{hostpart}/{database}?driver="
        f"{driver_q}"
    )
    config.set_main_option("sqlalchemy.url", sqlalchemy_url)
except Exception:
    pass


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata.metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        version_table_schema="dbo",
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    section = config.get_section(config.config_ini_section) or {}
    connectable = engine_from_config(
        section,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata.metadata,
            compare_type=True,
            version_table_schema="dbo",
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
