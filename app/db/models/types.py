"""Column types shared by every model."""

from datetime import datetime, timezone

from sqlalchemy import DateTime
from sqlalchemy.engine import Dialect
from sqlalchemy.types import TypeDecorator


def utcnow() -> datetime:
    """The current time as a timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)


class UTCDateTime(TypeDecorator[datetime]):
    """Stores naive UTC and returns aware UTC, identically on SQLite and Postgres.

    SQLite drops tzinfo silently, so without this type a value read back would
    be naive while `utcnow()` is aware, and comparing them raises. Naive input
    is rejected so a missing timezone is caught where the value is written.
    """

    impl = DateTime()
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError(f"naive datetime {value!r}; pass a timezone-aware UTC value")
        return value.astimezone(timezone.utc).replace(tzinfo=None)

    def process_result_value(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        if value is None:
            return None
        return value.replace(tzinfo=timezone.utc)
