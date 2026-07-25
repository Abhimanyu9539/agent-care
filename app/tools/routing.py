"""The tools the routing agent's LLM may call.

They are made fresh for each run, tied to that run's patient. get_patient_history takes no arguments,
so the LLM never sees a patient id and can never ask for someone else's records.
"""

from langchain_core.tools import BaseTool, tool
from sqlalchemy.orm import Session

from app.services import appointment, department


def make_routing_tools(db: Session, patient_id: int) -> list[BaseTool]:
    @tool
    def list_departments() -> list[dict]:
        """The hospital's departments: code, name, what each one handles, and words that point to it."""
        return [
            {"code": d["code"], "name": d["name"], "description": d["description"], "hints": d["routing_hints"]}
            for d in department.list_departments(db)
        ]

    @tool
    def get_patient_history() -> list[dict]:
        """This patient's visits, oldest first: department code, visit type, status and date."""
        return [
            {"department": v["department"], "visit_type": v["visit_type"], "status": v["status"], "date": str(v["date"])}
            for v in appointment.list_patient_visits(db, patient_id)
        ]

    return [list_departments, get_patient_history]
