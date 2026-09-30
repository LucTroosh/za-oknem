from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app import models  # noqa: F401 — import registers models on Base.metadata
from app.config import settings
from app.db import Base
from app.geometry import MultiPolygon4326

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def include_object(obj, name, type_, reflected, compare_to) -> bool:
    # PostGIS (ADR-019) owns spatial_ref_sys; without this `alembic check` would want
    # to drop it, since it reflects a table no model declares.
    return not (type_ == "table" and reflected and name == "spatial_ref_sys")


def compare_type(context, inspected_column, metadata_column, inspected_type, metadata_type):
    # `geometry` reflects as NullType, so the default comparison can't see it match.
    # None = fall back to alembic's default for every other column.
    return False if isinstance(metadata_type, MultiPolygon4326) else None


def get_url() -> str:
    return settings.database_url


def run_migrations_offline() -> None:
    context.configure(
        url=get_url(),
        target_metadata=target_metadata,
        include_object=include_object,
        compare_type=compare_type,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = get_url()
    connectable = engine_from_config(configuration, prefix="sqlalchemy.", poolclass=pool.NullPool)

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_object=include_object,
            compare_type=compare_type,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
