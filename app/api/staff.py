"""Staff pages. Every route here needs the STAFF or ADMIN role."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response
from sqlalchemy import RowMapping
from sqlalchemy.orm import Session

from app.auth.deps import require_role
from app.db.session import get_db
from app.services.appointment import list_upcoming_slots
from app.web import templates

staff_user = require_role("STAFF", "ADMIN")

router = APIRouter(prefix="/staff", dependencies=[Depends(staff_user)])


@router.get("/slots")
def slots(
    request: Request,
    user: Annotated[RowMapping, Depends(staff_user)],
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    """Upcoming appointment slots for every doctor."""
    rows = list_upcoming_slots(db, request.app.state.settings.hospital_tz)
    return templates.TemplateResponse(request, "staff/slots.html", {"user": user, "slots": rows})
