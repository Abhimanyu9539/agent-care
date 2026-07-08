"""Patient pages. Every route here needs the PATIENT role."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response
from sqlalchemy import RowMapping

from app.auth.deps import require_role
from app.web import templates

patient_user = require_role("PATIENT")

router = APIRouter(prefix="/patient", dependencies=[Depends(patient_user)])


@router.get("")
def home(request: Request, user: Annotated[RowMapping, Depends(patient_user)]) -> Response:
    """Placeholder patient home. The request form and appointments come later."""
    return templates.TemplateResponse(request, "home.html", {"user": user})
