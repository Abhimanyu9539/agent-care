"""Pages outside sign-in."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse, Response
from sqlalchemy import RowMapping

from app.auth.deps import current_user
from app.web import templates

router = APIRouter()


@router.get("/")
def home(request: Request, user: Annotated[RowMapping | None, Depends(current_user)]) -> Response:
    """Placeholder home showing who is signed in. Real patient and staff pages come later."""
    if user is None:
        return RedirectResponse("/auth/login", status_code=303)
    return templates.TemplateResponse(request, "home.html", {"user": user})
