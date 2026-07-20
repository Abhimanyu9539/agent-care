"""Patient API. Every route here needs the PATIENT role."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import RowMapping
from sqlalchemy.orm import Session

from app.auth.deps import require_role
from app.db.session import get_db
from app.services.patient import create_request, get_request

patient_user = require_role("PATIENT")

router = APIRouter(prefix="/api/patient", dependencies=[Depends(patient_user)])

User = Annotated[RowMapping, Depends(patient_user)]
Db = Annotated[Session, Depends(get_db)]

MAX_REQUEST_CHARS = 2000


class NewRequest(BaseModel):
    request_text: str = ""


@router.post("/requests", status_code=201)
def submit(user: User, db: Db, body: NewRequest) -> dict:
    """Save the request. Returns its id."""
    request_text = body.request_text.strip()
    if not request_text:
        raise HTTPException(status_code=400, detail="Please describe what you need.")
    if len(request_text) > MAX_REQUEST_CHARS:
        raise HTTPException(
            status_code=400, detail=f"Please keep your request to at most {MAX_REQUEST_CHARS} characters."
        )
    return {"id": create_request(db, user["id"], request_text)}


@router.get("/requests/{run_id}")
def show(run_id: int, user: User, db: Db) -> dict:
    """One request and its status.

    Another patient's request gets the same 404 as a missing one, so the API never reveals which ids exist.
    """
    run = get_request(db, run_id, user["id"])
    if run is None:
        raise HTTPException(status_code=404, detail="Request not found.")
    return dict(run)
