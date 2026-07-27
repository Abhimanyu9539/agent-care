"""The workflow: after a request is saved, the safety step decides what happens next, and an ordinary
request then goes to the routing step, which picks the department and visit type.

Needs the database running with the tables created (see README). The real LLM is never called:
`fake_llm` stands in for it, and without it the test settings have no API key, so the LLM step fails.
The fixtures and the test-account cleanup are in conftest.py.
The test client waits for background tasks, so each workflow has finished when `submit` returns.
"""

import uuid

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from langchain_core.tracers.context import collect_runs
from langgraph.runtime import Runtime
from pydantic import ValidationError
from sqlalchemy import text

from app.agents.coordinator.schema import CoordinatorPlan
from app.agents.routing.schema import RoutingVerdict
from app.agents.safety.agent import safety_intake
from app.graph.state import WorkflowContext
from app.services import department as department_service
from app.tools.routing import make_routing_tools


def _sign_up(app: FastAPI, role: str = "PATIENT") -> TestClient:
    """A client signed in as a new test user with this role."""
    client = TestClient(app)
    user = client.post(
        "/api/auth/register",
        json={
            "full_name": "Test Patient",
            "email": f"test-{uuid.uuid4().hex[:12]}@example.com",
            "password": "password123",
            "date_of_birth": "1990-05-01",
            "phone": "+91 90000 99999",
        },
    ).json()
    with app.state.engine.begin() as connection:
        connection.execute(text("UPDATE users SET role = :role WHERE id = :id"), {"role": role, "id": user["id"]})
    return client


def _submit(patient: TestClient, request_text: str) -> dict:
    """Submit a request and return how the patient sees it once the workflow has run."""
    run_id = patient.post("/api/patient/requests", json={"request_text": request_text}).json()["id"]
    return patient.get(f"/api/patient/requests/{run_id}").json()


def _rows(app: FastAPI, sql: str, run_id: int) -> list:
    with app.state.engine.connect() as connection:
        return connection.execute(text(sql), {"id": run_id}).all()


def _add_completed_visit(app: FastAPI, patient: TestClient, department_code: str) -> int:
    """Give a test patient an earlier, completed visit in this department. Returns their patient id."""
    user_id = patient.get("/api/auth/me").json()["id"]
    with app.state.engine.begin() as connection:
        return connection.execute(
            text(
                "INSERT INTO appointments (patient_id, department_id, doctor_id, slot_id, status, visit_type, reason) "
                "SELECT p.id, dep.id, doc.id, (SELECT min(id) FROM appointment_slots), 'COMPLETED', 'NEW', 'Test visit' "
                "FROM patient_profiles p, departments dep JOIN doctors doc ON doc.department_id = dep.id "
                "WHERE p.user_id = :user_id AND dep.code = :code LIMIT 1 "
                "RETURNING patient_id"
            ),
            {"user_id": user_id, "code": department_code},
        ).scalar_one()


def test_rules_decide_obvious_cases_without_the_llm(app: FastAPI, fake_llm) -> None:
    def safety(request_text: str) -> dict:
        state = {"run_id": 1, "request_text": request_text, "patient_name": "Test Patient"}
        return safety_intake(state, Runtime(context=WorkflowContext(settings=app.state.settings, db=None)))["safety"]

    assert safety("I have crushing chest pain right now")["category"] == "EMERGENCY"
    assert safety("What dose should I take?")["category"] == "CLINICAL_ADVICE"
    assert fake_llm.sent == []

    assert safety("Book a cardiology follow-up") == {
        "category": "ADMIN", "rule_id": None, "reason": "The fake LLM says so.", "source": "llm"
    }
    assert fake_llm.sent == ["Book a cardiology follow-up"]


def test_emergency_opens_an_urgent_case_for_staff(app: FastAPI) -> None:
    run = _submit(_sign_up(app), "I have crushing chest pain right now")

    assert run["status"] == "ESCALATED"
    assert run["safety"] == "EMERGENCY"
    cases = _rows(app, "SELECT type, priority, status FROM escalations WHERE workflow_run_id = :id", run["id"])
    assert cases == [("EMERGENCY", "URGENT", "OPEN")]
    steps = _rows(app, "SELECT seq, agent, node, outcome FROM workflow_steps WHERE run_id = :id", run["id"])
    assert steps == [(1, "safety", "safety_intake", "OK")]
    events = _rows(app, "SELECT action, actor_agent FROM audit_events WHERE workflow_run_id = :id ORDER BY id", run["id"])
    assert events == [("request.create", None), ("escalation.open", "safety"), ("workflow.status_change", "safety")]

    inbox = _sign_up(app, "STAFF").get("/api/staff/escalations").json()
    assert any(case["workflow_run_id"] == run["id"] and case["priority"] == "URGENT" for case in inbox)


def test_clinical_question_is_declined_without_a_case(app: FastAPI) -> None:
    run = _submit(_sign_up(app), "What dose of my BP tablets should I take?")

    assert run["status"] == "COMPLETED"
    assert run["safety"] == "CLINICAL_ADVICE"
    assert _rows(app, "SELECT id FROM escalations WHERE workflow_run_id = :id", run["id"]) == []
    blocked = _rows(
        app, "SELECT metadata FROM audit_events WHERE workflow_run_id = :id AND action = 'safety.blocked_input'", run["id"]
    )
    assert blocked == [({"source": "rules", "rule_id": "clinical_advice.dose"},)]


@pytest.mark.parametrize(
    ("category", "status", "cases"),
    [
        ("EMERGENCY", "ESCALATED", [("EMERGENCY", "URGENT")]),
        ("CLINICAL_ADVICE", "COMPLETED", []),
        ("ADMIN", "COMPLETED", []),
    ],
)
def test_the_llm_decides_when_no_rule_matches(app: FastAPI, fake_llm, category, status, cases) -> None:
    fake_llm.category = category

    run = _submit(_sign_up(app), "Please help me with my dad")

    assert (run["status"], run["safety"]) == (status, category)
    assert _rows(app, "SELECT type, priority FROM escalations WHERE workflow_run_id = :id", run["id"]) == cases
    [(outcome, llm_meta)] = _rows(
        app, "SELECT outcome, llm_meta FROM workflow_steps WHERE run_id = :id AND seq = 1", run["id"]
    )
    assert outcome == "OK"
    assert llm_meta == {
        "model": app.state.settings.llm_model, "prompt_version": "safety-v1", "tokens_in": 10, "tokens_out": 5
    }


def test_the_llm_never_sees_personal_details(app: FastAPI, fake_llm) -> None:
    _submit(_sign_up(app), "I am Test Patient, call me on +91 98765 43210 or write to me at tp@mail.com")

    # Once each for safety, the coordinator and routing: all masked.
    masked = "I am [NAME] [NAME], call me on [NUMBER] or write to me at [EMAIL]"
    assert fake_llm.sent == [masked, masked, masked]


def test_without_an_api_key_the_request_goes_to_staff(app: FastAPI) -> None:
    # No fake_llm and no API key, so the LLM call fails: the same path as a timeout or OpenRouter being down.
    run = _submit(_sign_up(app), "Please help me with my dad")

    assert (run["status"], run["safety"]) == ("ESCALATED", "UNCHECKED")
    cases = _rows(app, "SELECT type, priority, status FROM escalations WHERE workflow_run_id = :id", run["id"])
    assert cases == [("SYSTEM_FAILURE", "HIGH", "OPEN")]
    [(outcome, llm_meta)] = _rows(app, "SELECT outcome, llm_meta FROM workflow_steps WHERE run_id = :id", run["id"])
    assert outcome == "FAILED"
    assert llm_meta["error"] == "LLMNotConfigured"


def test_staff_see_the_timeline_and_patients_do_not(app: FastAPI) -> None:
    patient = _sign_up(app)
    run_id = _submit(patient, "I can't breathe")["id"]
    staff = _sign_up(app, "STAFF")

    shown = staff.get(f"/api/staff/runs/{run_id}").json()

    assert shown["run"]["status"] == "ESCALATED"
    assert shown["run"]["patient"] == "Test Patient"
    [step] = shown["steps"]
    assert (step["agent"], step["node"], step["outcome"]) == ("safety", "safety_intake", "OK")
    assert step["output"]["safety"]["rule_id"] == "emergency.breathing"
    assert step["llm_meta"] is None  # a rule decided, so the LLM was not asked
    # The timeline stores counts, never the patient's words.
    assert _rows(app, "SELECT input_summary FROM workflow_steps WHERE run_id = :id", run_id) == [
        ({"text_chars": 15, "attempt": 1},)
    ]
    assert staff.get("/api/staff/runs/999999999").status_code == 404
    assert patient.get(f"/api/staff/runs/{run_id}").status_code == 403


def test_staff_list_requests_with_how_each_was_decided(app: FastAPI, fake_llm) -> None:
    patient = _sign_up(app)
    routed = _submit(patient, "Book a cardiology visit")  # no rule matches: the (fake) LLM decides both steps
    emergency = _submit(patient, "I can't breathe")  # a rule decides, and routing never runs

    listed = {run["id"]: run for run in _sign_up(app, "STAFF").get("/api/staff/runs").json()}

    assert listed[routed["id"]]["safety"] == "ADMIN" and listed[routed["id"]]["safety_source"] == "llm"
    assert listed[routed["id"]]["intent"] == "BOOK"
    assert listed[routed["id"]]["department"] == "Cardiology"
    assert listed[routed["id"]]["routing"]["result"] == "ROUTED"
    assert (listed[emergency["id"]]["safety_source"], listed[emergency["id"]]["routing"]) == ("rules", None)
    assert patient.get("/api/staff/runs").status_code == 403


# Coordinator


def test_the_coordinator_hands_the_request_to_routing_and_finishes(app: FastAPI, fake_llm) -> None:
    fake_llm.plan = CoordinatorPlan(intent="RESCHEDULE", plan=["routing", "routing"], reason="Move a visit.")

    run = _submit(_sign_up(app), "Please move my cardiology visit to Friday")

    assert run["status"] == "COMPLETED"
    steps = _rows(app, "SELECT agent, node, output, llm_meta FROM workflow_steps WHERE run_id = :id ORDER BY seq", run["id"])
    # The plan named routing twice, but each agent runs once.
    assert [step[:2] for step in steps] == [
        ("safety", "safety_intake"), ("coordinator", "coordinator"), ("routing", "route_request"), ("coordinator", "coordinator")
    ]
    first_turn, last_turn = steps[1], steps[3]
    assert first_turn[2]["coordinator"] == {
        "result": "PLANNED", "intent": "RESCHEDULE", "plan": ["routing"], "reason": "Move a visit."
    }
    assert first_turn[2]["next_agent"] == "routing" and first_turn[3]["prompt_version"] == "coordinator-v1"
    # The last turn just follows the plan: no LLM call.
    assert (last_turn[2], last_turn[3]) == ({"next_agent": "finish", "plan": []}, None)
    assert _rows(app, "SELECT intent FROM workflow_runs WHERE id = :id", run["id"]) == [("RESCHEDULE",)]


def test_the_coordinator_can_only_plan_agents_that_exist() -> None:
    with pytest.raises(ValidationError):
        CoordinatorPlan(intent="BOOK", plan=["billing"], reason="No such agent.")
    with pytest.raises(ValidationError):
        CoordinatorPlan(intent="BOOK", plan=[], reason="Nothing to do.")


def test_when_the_coordinator_llm_fails_the_request_goes_to_staff(app: FastAPI, fake_llm) -> None:
    fake_llm.plan = TimeoutError()

    run = _submit(_sign_up(app), "Please help me with my dad")

    assert run["status"] == "ESCALATED"
    cases = _rows(app, "SELECT type, priority FROM escalations WHERE workflow_run_id = :id", run["id"])
    assert cases == [("SYSTEM_FAILURE", "NORMAL")]
    steps = _rows(app, "SELECT node, outcome FROM workflow_steps WHERE run_id = :id ORDER BY seq", run["id"])
    assert steps == [("safety_intake", "OK"), ("coordinator", "FAILED")]  # routing never ran


# Routing


def test_routing_tools_take_no_patient_id_and_see_only_this_patient(app: FastAPI) -> None:
    patient_id = _add_completed_visit(app, _sign_up(app), "cardiology")
    _add_completed_visit(app, _sign_up(app), "dermatology")  # someone else's visit

    with app.state.session_factory() as db:
        list_departments, get_patient_history = make_routing_tools(db, patient_id)

        assert list_departments.args == {} and get_patient_history.args == {}  # nothing for the LLM to fill in
        assert {"cardiology", "dermatology"} <= {d["code"] for d in list_departments.invoke({})}
        [visit] = get_patient_history.invoke({})
    assert (visit["department"], visit["visit_type"], visit["status"]) == ("cardiology", "NEW", "COMPLETED")


def test_a_follow_up_goes_to_the_department_the_patient_visited(app: FastAPI, fake_llm) -> None:
    patient = _sign_up(app)
    _add_completed_visit(app, patient, "cardiology")
    fake_llm.route = RoutingVerdict(department="cardiology", visit_type="FOLLOW_UP", confidence=0.9, reason="Seen before.")

    run = _submit(patient, "Book my follow-up next week")

    assert (run["status"], run["department"], run["visit_type"], run["changed_to_new"]) == (
        "COMPLETED", "Cardiology", "FOLLOW_UP", False
    )
    [(department,)] = _rows(
        app, "SELECT d.code FROM workflow_runs r JOIN departments d ON d.id = r.department_id WHERE r.id = :id", run["id"]
    )
    assert department == "cardiology"
    [(outcome, tool_calls)] = _rows(
        app, "SELECT outcome, tool_calls FROM workflow_steps WHERE run_id = :id AND node = 'route_request'", run["id"]
    )
    assert (outcome, tool_calls) == ("OK", fake_llm.TOOL_CALLS)


def test_a_follow_up_without_an_earlier_visit_becomes_a_new_visit(app: FastAPI, fake_llm) -> None:
    fake_llm.route = RoutingVerdict(department="cardiology", visit_type="FOLLOW_UP", confidence=0.9, reason="Asked.")

    run = _submit(_sign_up(app), "Book a cardiology follow-up")

    assert (run["status"], run["department"], run["visit_type"], run["changed_to_new"]) == (
        "COMPLETED", "Cardiology", "NEW", True
    )


@pytest.mark.parametrize(("department", "confidence"), [("neurology", 0.9), ("cardiology", 0.3)])
def test_an_unknown_department_or_low_confidence_goes_to_staff(app: FastAPI, fake_llm, department, confidence) -> None:
    fake_llm.route = RoutingVerdict(department=department, visit_type="NEW", confidence=confidence, reason="Unsure.")

    run = _submit(_sign_up(app), "Please help me with my dad")

    assert (run["status"], run["department"]) == ("ESCALATED", None)
    cases = _rows(app, "SELECT type, priority, reason FROM escalations WHERE workflow_run_id = :id", run["id"])
    assert cases == [("LOW_CONFIDENCE", "NORMAL", f"Not sure which department. Best guess: {department} ({confidence:.0%}).")]


def test_when_the_routing_llm_fails_the_request_goes_to_staff(app: FastAPI, fake_llm) -> None:
    fake_llm.route = TimeoutError()

    run = _submit(_sign_up(app), "Please help me with my dad")

    assert run["status"] == "ESCALATED"
    cases = _rows(app, "SELECT type, priority FROM escalations WHERE workflow_run_id = :id", run["id"])
    assert cases == [("SYSTEM_FAILURE", "NORMAL")]
    [(outcome, llm_meta)] = _rows(
        app, "SELECT outcome, llm_meta FROM workflow_steps WHERE run_id = :id AND node = 'route_request'", run["id"]
    )
    assert (outcome, llm_meta["error"]) == ("FAILED", "TimeoutError")


# Failures and retry


def test_an_unexpected_error_marks_the_request_failed_and_staff_can_retry_it(
    app: FastAPI, fake_llm, monkeypatch: pytest.MonkeyPatch
) -> None:
    def database_gone(db):
        raise RuntimeError("the database went away, with patient text in the message")

    # Breaks the routing step outside its LLM call, which the agents do not handle themselves.
    list_departments = department_service.list_departments
    monkeypatch.setattr(department_service, "list_departments", database_gone)
    patient = _sign_up(app)

    run = _submit(patient, "Book a cardiology visit")

    assert run["status"] == "FAILED"
    [(error, attempt)] = _rows(app, "SELECT error, attempt FROM workflow_runs WHERE id = :id", run["id"])
    # The error's type only: its text could hold patient data.
    assert (error, attempt) == ({"code": "RuntimeError", "message": "Stopped unexpectedly after coordinator."}, 1)
    events = _rows(
        app, "SELECT metadata FROM audit_events WHERE workflow_run_id = :id AND action = 'workflow.status_change'", run["id"]
    )
    assert events == [({"from": "RUNNING", "to": "FAILED", "error": "RuntimeError"},)]

    monkeypatch.setattr(department_service, "list_departments", list_departments)  # the database is back
    fake_llm.route = RoutingVerdict(department="cardiology", visit_type="NEW", confidence=0.9, reason="Back up.")
    staff = _sign_up(app, "STAFF")

    response = staff.post(f"/api/staff/runs/{run['id']}/retry")

    assert (response.status_code, response.json()) == (202, {"attempt": 2})
    assert patient.get(f"/api/patient/requests/{run['id']}").json()["status"] == "COMPLETED"
    steps = staff.get(f"/api/staff/runs/{run['id']}").json()["steps"]
    # The first attempt's steps stay as history; the retry's steps follow them, from the start.
    assert [(s["seq"], s["node"], s["attempt"]) for s in steps] == [
        (1, "safety_intake", 1), (2, "coordinator", 1),
        (3, "safety_intake", 2), (4, "coordinator", 2), (5, "route_request", 2), (6, "coordinator", 2),
    ]
    retried = _rows(app, "SELECT metadata FROM audit_events WHERE workflow_run_id = :id AND action = 'workflow.retry'", run["id"])
    assert retried == [({"from": "FAILED", "attempt": 2},)]
    # The requests list shows it once, decided by the latest attempt.
    listed = [r for r in staff.get("/api/staff/runs").json() if r["id"] == run["id"]]
    assert [(r["status"], r["routing"]["result"]) for r in listed] == [("COMPLETED", "ROUTED")]


def test_a_stuck_request_can_be_retried(app: FastAPI, fake_llm) -> None:
    patient = _sign_up(app)
    run_id = _submit(patient, "Book a cardiology visit")["id"]
    # As if the server restarted mid-run: still RUNNING, and no progress for 11 minutes.
    with app.state.engine.begin() as connection:
        connection.execute(
            text("UPDATE workflow_runs SET status = 'RUNNING', updated_at = now() - interval '11 minutes' WHERE id = :id"),
            {"id": run_id},
        )
    staff = _sign_up(app, "STAFF")

    assert staff.get(f"/api/staff/runs/{run_id}").json()["run"]["stuck"] is True
    assert patient.get(f"/api/patient/requests/{run_id}").json()["stuck"] is True

    assert staff.post(f"/api/staff/runs/{run_id}/retry").status_code == 202
    assert patient.get(f"/api/patient/requests/{run_id}").json()["status"] == "COMPLETED"


def test_only_failed_or_stuck_requests_can_be_retried(app: FastAPI, fake_llm) -> None:
    patient = _sign_up(app)
    completed = _submit(patient, "Book a cardiology visit")["id"]
    staff = _sign_up(app, "STAFF")

    response = staff.post(f"/api/staff/runs/{completed}/retry")

    assert (response.status_code, response.json()["detail"]) == (409, "Only a failed or stuck request can be retried.")
    assert staff.post("/api/staff/runs/999999999/retry").status_code == 404
    assert patient.post(f"/api/staff/runs/{completed}/retry").status_code == 403


# Tracing


def test_the_trace_names_the_request_and_attempt(app: FastAPI, fake_llm) -> None:
    patient = _sign_up(app)

    with collect_runs() as traces:  # collects what LangSmith would be sent
        run_id = _submit(patient, "Book a cardiology visit")["id"]

    [trace] = traces.traced_runs
    assert trace.name == "workflow"
    assert (trace.extra["metadata"]["run_id"], trace.extra["metadata"]["attempt"]) == (run_id, 1)
