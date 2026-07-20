"""Staff API. Every route here needs the STAFF or ADMIN role."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.auth.deps import require_role
from app.db.session import get_db
from app.services.appointment import list_upcoming_slots

staff_user = require_role("STAFF", "ADMIN")

router = APIRouter(prefix="/api/staff", dependencies=[Depends(staff_user)])


@router.get("/slots")
def slots(request: Request, db: Annotated[Session, Depends(get_db)]) -> list[dict]:
    """Upcoming appointment slots for every doctor. `starts_at` is in the hospital time zone."""
    rows = list_upcoming_slots(db, request.app.state.settings.hospital_tz)
    return [dict(row) for row in rows]
