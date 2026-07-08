"""Pages outside sign-in."""

from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy import RowMapping

from app.auth.deps import current_user

router = APIRouter()


@router.get("/")
def home(user: Annotated[RowMapping | None, Depends(current_user)]) -> RedirectResponse:
    """Send each visitor to the start page for their role."""
    if user is None:
        return RedirectResponse("/auth/login", status_code=303)
    if user["role"] == "PATIENT":
        return RedirectResponse("/patient", status_code=303)
    return RedirectResponse("/staff/slots", status_code=303)
