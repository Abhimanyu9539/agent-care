"""Declarative base, engine construction, and the request-scoped session dependency."""

from collections.abc import Iterator
from typing import Any

from fastapi import Request
from sqlalchemy import Engine, MetaData, create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

# Deterministic constraint names, so they are unique per schema on Postgres.
NAMING_CONVENTION = {
    "ix": "ix_%(table_name)s_%(column_0_N_name)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


def _enable_sqlite_foreign_keys(dbapi_connection: Any, connection_record: Any) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def make_engine(url: str) -> Engine:
    """Create an engine; SQLite gets cross-thread access and enforced foreign keys."""
    if url.startswith("sqlite"):
        # FastAPI's threadpool and BackgroundTasks share one engine.
        engine = create_engine(url, connect_args={"check_same_thread": False})
        # SQLite ignores FOREIGN KEY constraints unless enabled per connection.
        event.listen(engine, "connect", _enable_sqlite_foreign_keys)
        return engine
    return create_engine(url, pool_pre_ping=True)


def make_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Sessions keep loaded attributes after commit so callers can return rows."""
    return sessionmaker(bind=engine, expire_on_commit=False)


def get_db(request: Request) -> Iterator[Session]:
    """FastAPI dependency: one session per request, from the app's own factory."""
    session = request.app.state.session_factory()
    try:
        yield session
    finally:
        session.close()
