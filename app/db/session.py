"""Declarative base, engine construction, and the request-scoped session dependency."""

from collections.abc import Iterator

from fastapi import Request
from sqlalchemy import Engine, MetaData, create_engine
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


def make_engine(url: str) -> Engine:
    """Create a Postgres engine; pre-ping replaces connections the server has dropped.

    The connect timeout makes requests fail fast when the database is unreachable,
    instead of waiting forever on a connection that never answers.
    """
    return create_engine(url, pool_pre_ping=True, connect_args={"connect_timeout": 5})


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
