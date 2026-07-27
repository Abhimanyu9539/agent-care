"""Staff API. Every route here needs the STAFF or ADMIN role."""

from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, Response
from sqlalchemy import RowMapping
from sqlalchemy.orm import Session

from app.auth.deps import require_role
from app.db.session import get_db
from app.graph.runner import run_request
from app.services.appointment import list_upcoming_slots
from app.services.escalation import list_open_escalations, resolve_escalation
from app.services.workflow import get_run, list_runs, list_steps, start_retry

staff_user = require_role("STAFF", "ADMIN")

router = APIRouter(prefix="/api/staff", dependencies=[Depends(staff_user)])

User = Annotated[RowMapping, Depends(staff_user)]
Db = Annotated[Session, Depends(get_db)]


@router.get("/slots")
def slots(request: Request, db: Db) -> list[dict]:
    """Upcoming appointment slots for every doctor. `starts_at` is in the hospital time zone."""
    rows = list_upcoming_slots(db, request.app.state.settings.hospital_tz)
    return [dict(row) for row in rows]


@router.get("/escalations")
def escalations(db: Db) -> list[dict]:
    """Open cases handed to staff, most urgent first."""
    return [dict(row) for row in list_open_escalations(db)]


@router.get("/runs")
def runs(db: Db) -> list[dict]:
    """The newest requests, with how the safety and routing steps decided each one."""
    return [dict(row) for row in list_runs(db)]


@router.get("/runs/{run_id}")
def run(run_id: int, db: Db) -> dict:
    """One request with its agent timeline: every step the workflow ran, in order."""
    found = get_run(db, run_id)
    if found is None:
        raise HTTPException(status_code=404, detail="Request not found.")
    return {"run": dict(found), "steps": [dict(step) for step in list_steps(db, run_id)]}


@router.post("/runs/{run_id}/retry", status_code=202)
def retry(run_id: int, request: Request, user: User, db: Db, background: BackgroundTasks) -> dict:
    """Run a failed or stuck request again from the start, in the background. 409 when it is neither."""
    found = get_run(db, run_id)
    if found is None:
        raise HTTPException(status_code=404, detail="Request not found.")
    attempt = start_retry(db, found, user["id"])
    if attempt is None:
        raise HTTPException(status_code=409, detail="Only a failed or stuck request can be retried.")
    background.add_task(run_request, request.app.state.session_factory, request.app.state.settings, run_id)
    return {"attempt": attempt}


@router.post("/escalations/{escalation_id}/resolve", status_code=204)
def resolve(escalation_id: int, user: User, db: Db) -> Response:
    """Close a case. 404 when there is no open case with that id, such as one already resolved."""
    if not resolve_escalation(db, escalation_id, user["id"]):
        raise HTTPException(status_code=404, detail="This case is not open any more.")
    return Response(status_code=204)
