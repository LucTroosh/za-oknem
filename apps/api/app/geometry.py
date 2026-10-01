"""PostGIS column type without a geoalchemy2 dependency (ADR-019).

Geometry is only ever written/queried through raw PostGIS SQL (`ST_Covers` etc.), never
materialised in Python, so a thin type that emits `geometry(MultiPolygon,4326)` DDL is
enough. On non-PostgreSQL dialects (the SQLite unit-test engine) it degrades to TEXT, so
`Base.metadata.create_all` keeps working; PostGIS behaviour is covered by the `postgis`
tests, which run wherever a PostGIS database is reachable (CI).
"""

from sqlalchemy import Text
from sqlalchemy.types import TypeDecorator, UserDefinedType


class _PgGeometry(UserDefinedType):
    cache_ok = True

    def get_col_spec(self, **kw) -> str:
        return "geometry(MultiPolygon,4326)"


class MultiPolygon4326(TypeDecorator):
    impl = Text
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(_PgGeometry())
        return dialect.type_descriptor(Text())
