"""Request dependencies for the signed-in user."""

from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy import RowMapping
from sqlalchemy.orm import Session

from app.auth.users import get_user
from app.db.session import get_db


def current_user(request: Request, db: Annotated[Session, Depends(get_db)]) -> RowMapping | None:
    """The signed-in, active user, or None.

    Only the user id lives in the session cookie, so the role and active flag are
    read fresh on every request. A deactivated user is signed out on their next one.
    """
    user_id = request.session.get("user_id")
    if user_id is None:
        return None
    user = get_user(db, user_id)
    if user is None or not user["is_active"]:
        request.session.clear()
        return None
    return user
