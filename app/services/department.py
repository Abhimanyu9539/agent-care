"""Plain-SQL queries for departments."""

from collections.abc import Sequence

from sqlalchemy import RowMapping, text
from sqlalchemy.orm import Session


def list_departments(db: Session) -> Sequence[RowMapping]:
    """The active departments, with what each one handles."""
    return db.execute(
        text("SELECT id, code, name, description, routing_hints FROM departments WHERE active ORDER BY id")
    ).mappings().all()
