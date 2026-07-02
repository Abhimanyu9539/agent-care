"""Shared test setup.

Environment defaults are set before any test imports `app.main`,
which builds the app at import time and needs `SECRET_KEY`.
"""

import os
from collections.abc import Iterator
from pathlib import Path

import pytest
from sqlalchemy import Engine
from sqlalchemy.orm import Session

os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("APP_ENV", "test")

from app.db.session import Base, make_engine, make_session_factory  # noqa: E402


@pytest.fixture
def engine(tmp_path: Path) -> Iterator[Engine]:
    """An empty schema in a throwaway SQLite file."""
    engine = make_engine(f"sqlite:///{tmp_path / 'test.db'}")
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def session(engine: Engine) -> Iterator[Session]:
    with make_session_factory(engine)() as session:
        yield session
