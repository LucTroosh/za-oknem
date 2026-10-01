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


# Tables created by extensions (PostGIS' spatial_ref_sys, ...), filled from the catalog on
# connect. Without skipping them `alembic check` wants to drop tables no model declares.
_EXTENSION_TABLES: set[str] = set()
_EXTENSION_TABLES_SQL = """
SELECT c.relname FROM pg_class c
JOIN pg_depend d ON d.classid = 'pg_class'::regclass AND d.objid = c.oid AND d.deptype = 'e'
WHERE c.relkind IN ('r', 'p') AND c.relnamespace = current_schema()::regnamespace
"""


def include_object(obj, name, type_, reflected, compare_to) -> bool:
    return not (
        type_ == "table" and reflected and (name == "spatial_ref_sys" or name in _EXTENSION_TABLES)
    )


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
        if connection.dialect.name == "postgresql":
            _EXTENSION_TABLES.update(
                r[0] for r in connection.exec_driver_sql(_EXTENSION_TABLES_SQL)
            )
            connection.commit()
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
