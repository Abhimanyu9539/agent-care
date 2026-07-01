# AgentCare Implementation Plan (LangGraph edition)

An ordered build guide for the AgentCare hackathon submission. Each step says what to create, how to implement it, and a "done when" check. Finish a step's check before starting the next one; every later step depends on the earlier ones.

The rubric rewards one thing above all: every path must be real and wired end to end (route -> service -> agent -> tool -> database -> persisted result). Anything hardcoded scores zero. Keep that in mind at every step.

---

## Stack decisions (fixed for the project)

| Concern | Choice | Why |
|---|---|---|
| Web | FastAPI + Jinja2 templates + python-multipart | Server-rendered forms are enough and count as a real UI |
| ORM / DB | SQLAlchemy 2.x; SQLite by default; `DATABASE_URL` switchable to Postgres | Persistent SQL with zero setup |
| Auth | Starlette `SessionMiddleware` (signed cookie via itsdangerous) + `bcrypt` | Simple, enforced in the backend |
| LLM | `langchain-anthropic` `ChatAnthropic`; model id from `LLM_MODEL` (default `claude-opus-5`) | One chat model shared by every agent |
| Agents | LangChain `create_agent` for the two tool-calling agents; `with_structured_output` for the four classifier / planner agents | Real tool loops where they matter, typed JSON everywhere else |
| Orchestration | LangGraph `StateGraph` as the Coordinator; `SqliteSaver` checkpointer; `interrupt()` for human approval | Durable state after every node, resumable runs, native human-in-the-loop |
| Files | Local disk under `UPLOAD_DIR`; sha256 checksum; `pypdf` for text extraction | Real ingestion logic, real duplicate detection |
| Tests | pytest + FastAPI `TestClient` + `InMemorySaver` + fake agent runnables | No API key needed to run tests or CI |
| Python | 3.11 or newer | LangChain 1.x and the Anthropic SDK need 3.10+ |

Two persistence layers work together and both are required:

- **LangGraph checkpoints** (`checkpoints.db` via `SqliteSaver`) hold the exact graph state so a run can pause at an interrupt or a crash and resume from the same node.
- **`workflow_runs` table** (your own SQL) mirrors a summary of that state (current step, status, the JSON values) so the UI, staff queue, and audit trail read from ordinary rows. The runner (Step 7) keeps the two in sync after every invoke.

---

## Folder layout

Create the tree in Step 1 and fill it in over the later steps.

```
agent-care/
  agentcare/
    __init__.py
    main.py                 # app factory, middleware, router registration
    config.py               # Settings (pydantic-settings) read from .env
    db/
      base.py               # engine, SessionLocal, get_db dependency
      models.py             # all ORM models
      seed.py               # synthetic data
    auth/
      security.py           # hash_password / verify_password
      deps.py               # current_user, require_role
    services/               # the TOOLS: plain functions over a Session
      audit.py
      errors.py
      patients.py
      departments.py
      availability.py
      appointments.py
      documents.py
      reminders.py
      notifications.py
      escalations.py
    llm/
      factory.py            # get_chat_model(settings); structured(schema) helper
      errors.py             # LLMUnavailable, LLMRefusal
    agents/
      schemas.py            # Pydantic I/O contracts for every agent
      prompts.py            # load_prompt(name) -> str
      safety.py             # structured-output agent
      planner.py            # Coordinator's planning + confirmation calls
      routing.py            # structured-output agent
      appointment.py        # create_agent + @tool wrappers
      document.py           # create_agent + @tool wrappers
      follow_up.py          # structured-output agent
      deps.py               # Deps dataclass: session_factory, settings, agents
    workflow/
      state.py              # WorkflowState TypedDict (graph state)
      nodes.py              # one function per graph node
      graph.py              # build_graph(deps, checkpointer)
      runner.py             # start_run, resume_run, retry_run, sync_run
    prompts/                # one .md file per agent
    web/
      routers/              # auth.py, patient.py, staff.py
      templates/            # base.html + one template per page
      static/style.css
    jobs/
      reminders.py          # due-reminder runner, incomplete-workflow detector
  scripts/
    init_db.py
    run_jobs.py
  tests/
  .env.example
  .gitignore
  requirements.txt
  README.md
  .github/workflows/agentcare-checks.yml
```

---

## Step 1 - Skeleton, configuration, dependencies

**Goal:** the app boots, configuration loads from the environment, nothing else yet.

**Create**

- `requirements.txt`:
  `fastapi`, `uvicorn[standard]`, `jinja2`, `python-multipart`, `sqlalchemy`, `pydantic`, `pydantic-settings`, `langchain>=1.0`, `langgraph>=1.0`, `langchain-anthropic`, `langgraph-checkpoint-sqlite`, `bcrypt`, `itsdangerous`, `pypdf`, `pytest`, `httpx`
  (`langchain`, `langgraph`, and `langchain-anthropic` all satisfy the CI check for an LLM client. `httpx` is needed by `TestClient`.)
- `agentcare/config.py`: a `Settings(BaseSettings)` class with `model_config = SettingsConfigDict(env_file=".env")` and these fields:

  | Variable | Default | Purpose |
  |---|---|---|
  | `APP_ENV` | `development` | `development` / `test` / `production` |
  | `SECRET_KEY` | none, required | session cookie signing |
  | `DATABASE_URL` | `sqlite:///./agentcare.db` | SQLAlchemy URL for application tables |
  | `CHECKPOINT_DB` | `./checkpoints.db` | SQLite file for LangGraph checkpoints |
  | `UPLOAD_DIR` | `./uploads` | document storage root |
  | `ANTHROPIC_API_KEY` | none | read by `ChatAnthropic` from the environment |
  | `LLM_MODEL` | `claude-opus-5` | model id |
  | `LLM_TIMEOUT_SECONDS` | `120` | per-request timeout |
  | `LLM_MAX_RETRIES` | `2` | SDK-level retries for 429 / 5xx / network errors |
  | `RUN_WORKFLOWS_INLINE` | `false` | `true` runs the graph synchronously in the request (used by tests) |
  | `MAX_UPLOAD_MB` | `10` | upload size cap |
  | `SENSITIVE_CANCEL_WINDOW_HOURS` | `24` | cancellations inside this window need staff approval |
  | `ROUTING_CONFIDENCE_THRESHOLD` | `0.6` | below this the routing result escalates |
  | `JOB_INTERVAL_SECONDS` | `60` | background reminder loop cadence, `0` disables |
  | `LANGSMITH_TRACING` | `false` | optional tracing; with `LANGSMITH_API_KEY` and `LANGSMITH_PROJECT` |

- `.env.example` with every variable above and placeholder values only.
- `.gitignore` containing at least `.env`, `uploads/`, `*.db`, `__pycache__/`, `.pytest_cache/`.
- `agentcare/main.py` with `create_app()` returning a FastAPI instance, `SessionMiddleware`, a static files mount, and `GET /health` returning `{"status": "ok"}`.

**Done when** `uvicorn agentcare.main:app --reload` serves `/health`, and starting without `SECRET_KEY` fails with a clear validation error.

---

## Step 2 - Data model, initialization, seed data

**Goal:** every persistent entity exists, and a seed script fills the database with synthetic data the demo will use.

**Models** (`agentcare/db/models.py`). Use SQLAlchemy 2 declarative with `Mapped[...]` annotations. All timestamps are UTC `datetime`. Store enums as short strings.

| Table | Columns and rules |
|---|---|
| `users` | id, name, email (unique), password_hash, role (`patient` / `staff`), created_at |
| `patient_profiles` | id, user_id (unique FK), date_of_birth, phone, preferred_language, emergency_contact, created_at, updated_at |
| `departments` | id, name (unique), description, active |
| `doctors` | id, department_id FK, name, active |
| `appointment_slots` | id, doctor_id FK, start_time, end_time, status (`free` / `booked` / `blocked`); index on (doctor_id, start_time) |
| `appointments` | id, patient_id FK, doctor_id FK, slot_id FK, status (`pending` / `confirmed` / `rescheduled` / `cancelled`), reason, workflow_run_id FK nullable, created_at, updated_at |
| `required_documents` | id, department_id FK, document_type, applies_to (`new` / `follow_up` / `any`) |
| `patient_documents` | id, patient_id FK, document_type, original_filename, storage_path, mime_type, size_bytes, checksum (sha256 hex), document_date nullable, classification_confidence, created_at; unique on (patient_id, checksum) |
| `workflow_runs` | id, patient_id FK, request_text, thread_id (unique, equals `str(id)`), current_step, status, state (JSON as Text), error nullable, created_at, updated_at |
| `reminders` | id, patient_id FK, appointment_id FK nullable, workflow_run_id FK nullable, reminder_type, scheduled_at, status (`scheduled` / `sent` / `cancelled`), message |
| `notifications` | id, patient_id FK, channel (`email` / `sms` / `in_app`, all simulated), subject, body, status, created_at, sent_at |
| `escalations` | id, workflow_run_id FK, patient_id FK, category (`emergency` / `clinical_request` / `sensitive` / `low_confidence` / `sensitive_action` / `system_error`), reason, status (`pending` / `approved` / `rejected`), reviewed_by FK nullable, review_note, created_at, reviewed_at |
| `audit_events` | id, actor_id FK nullable, actor_role, action, entity_type, entity_id, metadata (JSON as Text), created_at; index on (entity_type, entity_id) |

**Seed** (`agentcare/db/seed.py`, called by `scripts/init_db.py`). Idempotent: skip if any department exists.

- Four departments: Cardiology, Orthopaedics, Dermatology, General Medicine. Two doctors each.
- Slots: every weekday for the next 21 days, 09:00 to 17:00 in 30-minute blocks, per doctor. Mark a few as `booked` so conflicts are demonstrable.
- Required documents: Cardiology follow-up needs `ecg` and `blood_report`; Orthopaedics new visit needs `imaging`; Dermatology needs nothing; General Medicine needs `id_proof` for new visits.
- Three patient users and one staff user. Names like "Test Patient One", emails on `example.com`, password `password123` for all. Spread the ages so one patient is under 18 (used to demonstrate a sensitive-case escalation).
- One existing confirmed appointment for patient one, so the conflict check has something to hit.

`scripts/init_db.py` runs `Base.metadata.create_all(engine)` then seeds. The LangGraph checkpoint tables are created by `SqliteSaver.setup()` at app start (Step 7). Document both in the README as the migration step.

**Done when** running the script twice produces no duplicates, and `sqlite3 agentcare.db ".tables"` lists every table above.

---

## Step 3 - Authentication and backend role enforcement

**Goal:** login works, and every route and service call checks the role in code.

**Implement**

- `auth/security.py`: `hash_password(plain)` using `bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()`; `verify_password(plain, hashed)` with `bcrypt.checkpw`.
- `auth/deps.py`:
  - `get_current_user(request, db)` reads `request.session["user_id"]`, loads the user, and raises 401 (or redirects to `/login` for HTML routes) if absent.
  - `require_role(*roles)` returns a dependency that raises 403 when `user.role` is not in `roles`.
  - `get_current_patient(user, db)` returns the `PatientProfile` or 403 if the user is staff.
- Routes: `GET/POST /register` (creates user and profile in one transaction), `GET/POST /login`, `POST /logout`.
- **Service-level ownership checks.** Every service that touches a patient's row takes the acting user and asserts ownership or staff role. Example: `appointments.cancel(db, actor, appointment_id)` raises `PermissionError` if the actor is a patient and `appointment.patient_id != actor.profile.id`. Routers translate `PermissionError` into 403. This is what judges look for: hiding buttons is not enough.

**Done when** a patient cookie gets 403 on every `/staff/*` route, a staff cookie gets 403 on `/patient/*` routes, and a test proves a patient cannot cancel another patient's appointment by id.

---

## Step 4 - Tools (the service layer)

**Goal:** every capability the agents need exists as a plain Python function that takes a `Session`, does real work against the database, writes an audit event, and raises typed exceptions. LangChain `@tool` wrappers (Step 6) and graph nodes (Step 7) call these; nothing else touches the ORM.

**Shared pieces**

- `services/audit.py`: `log(db, *, actor_id, actor_role, action, entity_type, entity_id, metadata)`. Every tool below calls it. Use dotted action names such as `appointment.booked`, `document.duplicate_rejected`, `agent.routing.decision`.
- `services/errors.py`: `ToolError` base, plus `NotFound`, `SlotUnavailable`, `AppointmentConflict`, `DuplicateDocument`, `UnsupportedFileType`, `PermissionError`.

**Tools to implement** (the rubric needs three; build all of these)

1. **Patient records.** `patients.find_or_create(db, user)` returns the profile, creating it on first use. `patients.get_summary(db, patient_id)` returns a PII-light dict for prompts: patient_id, age band (`child` / `adult` / `senior`), preferred_language, count of active appointments. Never put a name, phone, or email into an LLM prompt.
2. **Department lookup.** `departments.list_active(db)` and `departments.find_by_name(db, name)` with case-insensitive match plus a small alias table (`heart` -> Cardiology, `bones` / `fracture` -> Orthopaedics, `skin` -> Dermatology).
3. **Availability.** `availability.list_slots(db, department_id, date_from, date_to, preference=None, limit=20)` returns free slots joined with doctor names, ordered by time. `preference` of `morning` or `afternoon` filters by hour.
4. **Appointments.** `appointments.book(db, actor, patient_id, slot_id, reason, workflow_run_id)` inside one transaction: reload the slot; raise `SlotUnavailable` unless status is `free`; check that no other active appointment for this patient overlaps the slot time, else `AppointmentConflict`; create the appointment as `confirmed`; set the slot to `booked`; audit; commit. **Idempotency guard:** if an active appointment already exists for this `workflow_run_id`, return it instead of booking again (this is what makes LangGraph retries safe). `reschedule(db, actor, appointment_id, new_slot_id)` frees the old slot and books the new one in the same transaction, setting status `rescheduled`. `cancel(db, actor, appointment_id)` frees the slot, cancels its reminders, and sets `cancelled`. All three enforce ownership from Step 3.
5. **Documents.** `documents.ingest(db, actor, patient_id, upload, workflow_run_id)`: validate extension (`pdf`, `png`, `jpg`, `jpeg`, `txt`) and size; read bytes; compute sha256; if a row with the same (patient_id, checksum) exists, audit `document.duplicate_rejected` and raise `DuplicateDocument(existing_id)`; otherwise write the file to `UPLOAD_DIR/patient_<id>/<checksum><ext>` and insert a row with `document_type = "unclassified"`. `documents.extract_text(db, document_id, max_chars=4000)` uses `pypdf` for PDFs and a plain read for text files; returns an empty string for images. `documents.set_classification(db, document_id, document_type, document_date, confidence)`. `documents.list_types_on_file(db, patient_id)`. `documents.missing_for(db, patient_id, department_id, visit_kind)` returns the required types minus the types the patient already has.
6. **Reminders.** `reminders.create(db, patient_id, appointment_id, reminder_type, scheduled_at, message, workflow_run_id)` and `reminders.cancel_for_appointment(db, appointment_id)`.
7. **Notifications.** `notifications.send(db, patient_id, channel, subject, body)` inserts a row with status `sent` and `sent_at = now`, and logs a line to the application logger. This is the simulated delivery mechanism; say so in the README.
8. **Escalations.** `escalations.create(db, workflow_run_id, patient_id, category, reason)`, `find_pending(db, workflow_run_id)`, `approve(db, staff_user, escalation_id, note)`, `reject(...)`. Approve and reject require the staff role and write audit events with the reviewer id.

**Done when** `tests/test_services.py` covers: booking the same slot twice raises `SlotUnavailable`; overlapping patient appointments raise `AppointmentConflict`; booking twice with the same `workflow_run_id` returns the same appointment; uploading the same bytes twice raises `DuplicateDocument`; missing documents are computed from the seed config; each tool leaves an audit row.

---

## Step 5 - LLM factory

**Goal:** one module that constructs the chat model and typed structured-output runnables. Agents receive these through `Deps`; nothing else instantiates a model.

**Implement** `agentcare/llm/factory.py`:

```python
from langchain_anthropic import ChatAnthropic
from langchain_core.runnables import Runnable
from pydantic import BaseModel


def get_chat_model(settings) -> ChatAnthropic:
    return ChatAnthropic(
        model=settings.LLM_MODEL,
        max_tokens=8192,
        timeout=settings.LLM_TIMEOUT_SECONDS,
        max_retries=settings.LLM_MAX_RETRIES,
    )


def structured(model: ChatAnthropic, schema: type[BaseModel]) -> Runnable:
    """A runnable that takes a list of messages and returns a validated `schema` instance."""
    return model.with_structured_output(schema)
```

`agentcare/llm/errors.py` defines `LLMUnavailable` (transient: rate limit, 5xx, network) and `LLMRefusal`. A small helper `call_structured(runnable, system, user)` builds `[SystemMessage(system), HumanMessage(user)]`, invokes, and translates the SDK's `RateLimitError`, `APIConnectionError`, and 5xx `APIStatusError` into `LLMUnavailable` so the graph's retry policy can target them. Any 4xx propagates as a hard failure.

Rules:

- The SDK already retries 429 and 5xx with backoff (`max_retries`). LangGraph's node-level `RetryPolicy` (Step 7) is the second layer. Do not write a third loop.
- Never ship a code path that fabricates an agent result when the model is unavailable. A failed call becomes a failed run with a retry button (Step 7).
- `Deps.structured_agents` is a dict from agent name to runnable, built once per app in `agents/deps.py`. Tests replace entries with `RunnableLambda` functions that return canned Pydantic objects.

**Done when** a small script builds the model, calls `structured(model, SomeTwoFieldSchema).invoke([...])`, and prints the parsed object.

---

## Step 6 - The agents

**Goal:** six agents, each with its own prompt file, its own input/output contract, and its own tool subset. Four are structured-output agents (one model call, typed result). Two are LangChain `create_agent` tool-calling agents (a real reason-act loop over `@tool` wrappers of Step 4 services). The Coordinator is the LangGraph graph itself plus its planning and confirmation calls. This step is the highest-weighted part of the rubric.

**Prompts.** One markdown file per agent under `prompts/`. Every file starts with the same boundary paragraph: the agent handles administrative coordination only; it never states or implies a diagnosis, a treatment, a medicine, or a dose; it never claims to replace a clinician. Then role-specific instructions and a description of the output fields.

**Contracts** (`agents/schemas.py`) and per-agent behaviour:

| Agent | Kind | Input | Output schema | Tools | Code-side validation |
|---|---|---|---|---|---|
| **Safety** | structured | request text, age band | `SafetyAssessment`: `emergency`, `clinical_request`, `sensitive`, `action: allow / allow_with_note / escalate / block`, `reason`, `patient_message` | none | A deterministic keyword screen runs first (chest pain, unconscious, overdose, suicide, bleeding heavily, etc.). Screen or model flagging `emergency` forces `block`. `clinical_request` alone yields `allow_with_note`: the administrative part proceeds and the confirmation carries a note to raise clinical questions with the clinician. Also called a second time on the confirmation text; any diagnosis wording blocks it. |
| **Coordinator (planner)** | structured, inside the graph | request text, patient summary, allowed steps | `WorkflowPlan`: `steps: list[route / appointment / documents / follow_up]`, `intent_summary`; second schema `ConfirmationText` | none (the graph executes) | Steps must be a subset of the enum, deduplicated, in canonical order. A document-only request yields `[route, documents, follow_up]`. Confirmation is composed only from persisted facts handed in by the confirm node. |
| **Routing** | structured | request text, active departments with descriptions | `RoutingDecision`: `intent: book / reschedule / cancel / upload_documents / status_inquiry / other`, `department_name`, `visit_kind: new / follow_up`, `confidence`, `needs_clarification`, `clarification_question`, `rationale` | `departments.find_by_name` (called by the node) | Name must resolve to an active row. Not found, or confidence below threshold, sends the graph to the staff-review interrupt. `intent = other` sends it to the patient-clarification interrupt. |
| **Appointment** | `create_agent` | department, visit kind, request text, patient id, existing appointment id when rescheduling | `SlotChoice`: `appointment_id`, `slot_id`, `summary`, `needs_clarification`, `clarification_question` (via `ToolStrategy`) | `@tool list_available_slots`, `@tool check_patient_conflicts`, `@tool book_slot`, `@tool reschedule_to_slot` | Tools are closures over a session, the acting user, and the run id (see below). `book_slot` is idempotent per run. The node verifies the returned `appointment_id` exists in the database and belongs to the patient before writing it into state. |
| **Document** | `create_agent` | list of newly uploaded document ids, department, visit kind | `DocumentReport`: `classified: list[{document_id, document_type, document_date, confidence}]`, `notes` (via `ToolStrategy`) | `@tool read_document_text`, `@tool list_types_on_file`, `@tool required_documents_for`, `@tool set_document_classification` | Ingest and checksum happen in code before the agent runs; duplicates never reach it. The node recomputes `missing` with `documents.missing_for` and stores that, not the model's opinion. The prompt forbids interpreting results; `notes` is administrative only. |
| **Follow-up** | structured | appointment time, department, missing types, visit kind | `FollowUpPlan`: `reminders: list[{type: appointment / document_missing / post_visit, offset_hours, channel, message}]` | `reminders.create`, `notifications.send` (called by the node) | Offsets clamped (appointment reminders 1 to 72 hours before; post-visit 1 to 14 days after). At most five reminders. The node converts offsets to absolute times and persists. |

**Tool-calling agents in detail** (`agents/appointment.py`, same pattern for `document.py`):

```python
from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy
from langchain.tools import tool


def make_appointment_tools(db, actor, patient_id, run_id):
    @tool
    def list_available_slots(department_id: int, days_ahead: int = 14, preference: str | None = None) -> list[dict]:
        """List free appointment slots for a department within the next `days_ahead` days."""
        return [s.as_dict() for s in availability.list_slots(db, department_id, ..., preference)]

    @tool
    def check_patient_conflicts(slot_id: int) -> dict:
        """Report whether the patient already has an appointment overlapping this slot."""
        ...

    @tool
    def book_slot(slot_id: int, reason: str) -> dict:
        """Book the slot for the patient. Returns the persisted appointment."""
        appt = appointments.book(db, actor, patient_id, slot_id, reason, run_id)
        return {"appointment_id": appt.id, "slot_id": appt.slot_id, "status": appt.status}

    return [list_available_slots, check_patient_conflicts, book_slot]


def run_appointment_agent(deps, db, actor, patient_id, run_id, payload: dict) -> SlotChoice:
    agent = create_agent(
        model=deps.chat_model,
        tools=make_appointment_tools(db, actor, patient_id, run_id),
        system_prompt=load_prompt("appointment"),
        response_format=ToolStrategy(SlotChoice),
    )
    result = agent.invoke({"messages": [{"role": "user", "content": json.dumps(payload)}]})
    return result["structured_response"]
```

Notes:

- Tools are created per call as closures so they carry the database session and the acting user without global state. The tool docstring is the description the model sees, so write it carefully.
- Every tool wrapper delegates to a Step 4 service, so audit rows are written automatically. Wrap `ToolError` subclasses and return their message as the tool result string, so the model can pick another slot instead of the agent crashing.
- The node writes an `agent.appointment.decision` audit row with the final `SlotChoice` and the count of tool calls taken from `result["messages"]`.
- For tests, `Deps` carries `appointment_agent_runner` and `document_agent_runner` callables. The real ones are the functions above; the fakes call `book_slot` on the first candidate and return a canned `SlotChoice`, so graph wiring is exercised without a model.

**Why this counts as six distinct agents:** each has its own prompt file, its own output schema, and a different tool subset, and the graph hands the output of one to the next through checkpointed state. Say this explicitly in the README with a table like the one above.

**Done when** each agent has a unit test proving that its output validation rejects bad values (unknown department, appointment id not in the database, out-of-range reminder offsets), and the two tool-calling agents have a test with a scripted fake model showing the tool loop runs.

---

## Step 7 - The LangGraph Coordinator graph and runner

**Goal:** the Coordinator as a `StateGraph`. Every node's result is checkpointed, humans are brought in with `interrupt()`, failures resume from the failed node, and the `workflow_runs` table always reflects the graph.

**State** (`workflow/state.py`), a `TypedDict` that is fully JSON-serializable:

```python
class WorkflowState(TypedDict, total=False):
    run_id: int
    patient_id: int
    request_text: str
    uploaded_document_ids: list[int]
    safety: dict            # SafetyAssessment.model_dump()
    plan: list[str]
    completed_steps: list[str]
    routing: dict           # department_id, intent, visit_kind, confidence
    appointment: dict       # appointment_id, slot_id, status
    documents: dict         # classified, missing
    follow_up: dict         # reminder_ids
    clarification_question: str | None
    patient_reply: str | None
    confirmation: str | None
    status: str             # running / rejected / completed
    errors: list[str]
```

**Nodes** (`workflow/nodes.py`). Each node is a closure produced by a factory that receives `Deps`, opens its own short-lived session with `deps.session_factory()`, commits, and returns a partial state update. Sessions must never be held across nodes, because a run can pause for hours at an interrupt.

| Node | What it does | Next |
|---|---|---|
| `safety_check` | keyword screen + Safety agent; writes `safety` | `safety_review` if action is `escalate` or `block`, else `plan` |
| `safety_review` | **interrupt only** (see rule below) with payload `{"kind": "staff_review", "category": ..., "reason": ...}`; the resume payload decides `status = rejected` or continue | `plan` or `END` |
| `plan` | Coordinator planning call; writes `plan` | `next_step` router |
| `route` | Routing agent; resolves department; writes `routing`, appends `route` to `completed_steps` | `route_review` on low confidence / unknown department; `patient_clarification` on `intent = other`; else `next_step` |
| `route_review` | **interrupt only**; resume payload may carry `department_id` chosen by staff, which is written into `routing` | `next_step` or `END` |
| `patient_clarification` | **interrupt only** with `{"kind": "patient_clarification", "question": ...}`; resume payload is the patient's reply, stored in `patient_reply` | back to `route` or `appointment` |
| `appointment` | for `cancel` / `reschedule` inside the sensitive window go to `action_review` first; otherwise run the Appointment agent; verify the appointment row; write `appointment` | `next_step`, or `patient_clarification` |
| `action_review` | **interrupt only** for `sensitive_action` | `appointment` or `END` |
| `documents` | Document agent over `uploaded_document_ids`; recompute `missing`; write `documents` | `next_step` |
| `follow_up` | Follow-up agent; persist reminders; write `follow_up` | `next_step` |
| `confirm` | reload appointment, doctor, slot, documents, reminders from the database; Coordinator confirmation call over those facts; Safety re-check; `notifications.send` in-app; `status = completed` | `END` |

`next_step(state)` returns the first entry in `plan` that is not in `completed_steps`, or `confirm` when the plan is exhausted, or `END` when `status == "rejected"`.

**The one rule that keeps interrupts correct:** a node that calls `interrupt()` does nothing else. LangGraph re-executes the whole node on resume, so an LLM call or a database write placed before `interrupt()` in the same node would run twice. Put the work in the node before, let the checkpoint capture it, and keep the review node down to the interrupt and a small state update.

**Graph** (`workflow/graph.py`):

```python
from langgraph.graph import StateGraph, START, END
from langgraph.types import RetryPolicy
from agentcare.llm.errors import LLMUnavailable

LLM_RETRY = RetryPolicy(max_attempts=3, retry_on=(LLMUnavailable,))


def build_graph(deps, checkpointer):
    g = StateGraph(WorkflowState)
    g.add_node("safety_check", make_safety_check(deps), retry_policy=LLM_RETRY)
    g.add_node("safety_review", make_safety_review(deps))
    g.add_node("plan", make_plan(deps), retry_policy=LLM_RETRY)
    g.add_node("route", make_route(deps), retry_policy=LLM_RETRY)
    g.add_node("route_review", make_route_review(deps))
    g.add_node("patient_clarification", make_patient_clarification(deps))
    g.add_node("appointment", make_appointment(deps), retry_policy=LLM_RETRY)
    g.add_node("action_review", make_action_review(deps))
    g.add_node("documents", make_documents(deps), retry_policy=LLM_RETRY)
    g.add_node("follow_up", make_follow_up(deps), retry_policy=LLM_RETRY)
    g.add_node("confirm", make_confirm(deps), retry_policy=LLM_RETRY)

    g.add_edge(START, "safety_check")
    g.add_conditional_edges("safety_check", after_safety, ["safety_review", "plan"])
    g.add_conditional_edges("safety_review", after_review, ["plan", END])
    g.add_conditional_edges("plan", next_step, ["route", "appointment", "documents", "follow_up", "confirm"])
    g.add_conditional_edges("route", after_route, ["route_review", "patient_clarification", "appointment", "documents", "follow_up", "confirm"])
    g.add_conditional_edges("route_review", next_step, ["appointment", "documents", "follow_up", "confirm", END])
    g.add_conditional_edges("patient_clarification", after_clarification, ["route", "appointment"])
    g.add_conditional_edges("appointment", after_appointment, ["action_review", "patient_clarification", "documents", "follow_up", "confirm"])
    g.add_conditional_edges("action_review", after_review, ["appointment", END])
    g.add_conditional_edges("documents", next_step, ["follow_up", "confirm"])
    g.add_edge("follow_up", "confirm")
    g.add_edge("confirm", END)
    return g.compile(checkpointer=checkpointer)
```

Checkpointer, created once in the app factory and stored on `app.state`:

```python
import sqlite3
from langgraph.checkpoint.sqlite import SqliteSaver

conn = sqlite3.connect(settings.CHECKPOINT_DB, check_same_thread=False)
checkpointer = SqliteSaver(conn)
checkpointer.setup()
```

Use `InMemorySaver` in tests and `PostgresSaver` (package `langgraph-checkpoint-postgres`) if you deploy on Postgres.

**Runner** (`workflow/runner.py`), the only place that invokes the graph:

```python
from langgraph.types import Command


def start_run(deps, graph, patient, request_text, uploads) -> WorkflowRun:
    # 1. ingest uploads in code (duplicates rejected here with a visible message)
    # 2. create the WorkflowRun row, thread_id = str(run.id)
    # 3. invoke
    config = {"configurable": {"thread_id": run.thread_id}}
    _invoke(deps, graph, run, initial_state, config)
    return run


def resume_run(deps, graph, run, resume_payload: dict):
    _invoke(deps, graph, run, Command(resume=resume_payload), config_for(run))


def retry_run(deps, graph, run):
    _invoke(deps, graph, run, None, config_for(run))   # None input resumes from the last checkpoint


def _invoke(deps, graph, run, graph_input, config):
    try:
        graph.invoke(graph_input, config)
    except Exception as e:
        mark_failed(run, str(e))       # checkpoint still points at the failed node
        raise
    finally:
        sync_run(deps, graph, run, config)


def sync_run(deps, graph, run, config):
    snapshot = graph.get_state(config)
    run.state = json.dumps(snapshot.values)
    interrupts = [i for task in snapshot.tasks for i in task.interrupts]
    if interrupts:
        payload = interrupts[0].value
        run.current_step = snapshot.next[0]
        if payload["kind"] == "staff_review":
            run.status = "awaiting_approval"
            if escalations.find_pending(db, run.id) is None:      # idempotent
                escalations.create(db, run.id, run.patient_id, payload["category"], payload["reason"])
        else:
            run.status = "awaiting_patient"
    elif snapshot.next:
        run.current_step = snapshot.next[0]      # paused by an exception; status set by mark_failed
    else:
        run.current_step = "completed"
        run.status = snapshot.values.get("status", "completed")
    db.commit()
```

Behaviour this gives you:

- **Persistence after every node**: LangGraph writes a checkpoint per node; `sync_run` mirrors it into `workflow_runs`.
- **Human approval**: the interrupt payload becomes an `Escalation` row; staff approval calls `resume_run` with `{"decision": "approve", "department_id": ..., "note": ...}`; rejection calls it with `{"decision": "reject"}`.
- **Patient clarification**: the status page shows the question; the reply form calls `resume_run` with `{"reply": "..."}`.
- **Failure and recovery**: transient LLM errors retry inside the node up to three times; a persistent failure marks the run `failed`; the staff retry button calls `retry_run`, which re-executes only the failed node. The `book_slot` idempotency guard means a retry never double-books.
- **Running it**: the request route calls `start_run` from a FastAPI `BackgroundTasks` job with its own session; when `RUN_WORKFLOWS_INLINE` is true it runs synchronously. The status page refreshes every few seconds while `status == running`.

**Done when** an end-to-end test with fake agents and `InMemorySaver` runs "cardiology follow-up next week with my old ECG" and asserts: one appointment row, one classified document, reminders present, run `completed`, an `agent.*.decision` audit row per agent. A second test makes the fake routing agent raise `LLMUnavailable` four times, asserts `failed`, then calls `retry_run` and asserts `completed` with still one appointment. A third test uses `SqliteSaver` on a temp file, interrupts at `route_review`, builds a fresh graph on the same file, resumes, and completes.

---

## Step 8 - Escalation and approval workflow

**Goal:** humans stay in control of emergencies, ambiguous routing, sensitive cases, and sensitive administrative actions. Approvals are persisted and resume the graph.

**Rules that create an interrupt** (thresholds in config, checks in the node before each review node):

| Category | Trigger | Review node |
|---|---|---|
| `emergency` | Safety agent or keyword screen | `safety_review`; the patient page shows the emergency guidance message immediately |
| `clinical_request` | Safety flags diagnosis / prescription / dosage and nothing administrative remains | `safety_review` |
| `sensitive` | Age band `child`, or Safety flags a sensitive topic | `safety_review` |
| `low_confidence` | Routing below threshold or department not found | `route_review` |
| `sensitive_action` | Cancel or reschedule inside `SENSITIVE_CANCEL_WINDOW_HOURS`, or third reschedule of the same appointment | `action_review` |
| `system_error` | Node failed after retries | no interrupt; `mark_failed` creates the escalation so staff see it in the same queue |

**Staff actions**

- `POST /staff/escalations/{id}/approve` with a note and, for `low_confidence`, a chosen department: `escalations.approve` sets status, reviewer, and time and audits; then `resume_run(run, {"decision": "approve", "department_id": ..., "note": ...})`.
- `POST /staff/escalations/{id}/reject` with a note: `escalations.reject`, then `resume_run(run, {"decision": "reject", "note": ...})`. The review node sets `status = rejected`, the graph ends, and `confirm` is skipped; the route then sends the patient an `in_app` notification with the note.
- Both routes use `require_role("staff")` and the service functions re-check the role.

**Done when** a test interrupts at `route_review`, approves as staff with a chosen department, and asserts the run continues to `completed` with that department; a test rejects and asserts `rejected` plus a notification; a test shows a patient cookie gets 403 on the approve route.

---

## Step 9 - Web interface

**Goal:** real pages wired to real logic. Visual polish is not scored; correctness is.

**Patient pages** (`web/routers/patient.py`, all behind `require_role("patient")`)

| Route | Content |
|---|---|
| `GET /patient` | dashboard: next appointment, open runs, unread notifications |
| `GET/POST /patient/profile` | edit profile fields |
| `GET/POST /patient/requests/new` | textarea for the request plus a multi-file upload field; POST calls `start_run` and redirects to the status page |
| `GET /patient/requests/{id}` | timeline rendered from `WorkflowRun.state`: one row per plan step with done / running / paused / failed; the clarification question with a reply form when `awaiting_patient`; the confirmation facts when completed; auto-refresh while running |
| `POST /patient/requests/{id}/reply` | calls `resume_run` with the reply |
| `GET /patient/appointments` | list with reschedule and cancel forms; reschedule shows free slots for the same department; both go through the graph as new runs with intent pre-set, so the sensitive-action review applies |
| `GET /patient/documents` | list with type, date, checksum prefix, and a missing-documents box per upcoming appointment |
| `GET /patient/reminders` | reminders and notifications |

**Staff pages** (`web/routers/staff.py`, all behind `require_role("staff")`)

| Route | Content |
|---|---|
| `GET /staff` | counts: pending escalations, running runs, failed runs, today's appointments |
| `GET /staff/requests` | all runs with status, step, patient id; link to detail |
| `GET /staff/requests/{id}` | the mirrored state JSON, the LangGraph checkpoint history from `graph.get_state_history(config)` (node name and timestamp per checkpoint), the audit trail for the run, a retry button for `failed` runs |
| `GET /staff/escalations`, `GET /staff/escalations/{id}` | queue and review form (approve with note and optional department, reject with note) |
| `GET/POST /staff/departments`, `/staff/doctors`, `/staff/slots` | create and toggle active; slot page can bulk-generate a day of slots for a doctor |
| `GET /staff/audit` | paginated audit events with filters on action and entity |

Use one `base.html` with a nav that changes by role, a flash-message block for tool errors (duplicate document, slot unavailable), and plain CSS.

**Done when** you can, in a browser: register, submit a request with a PDF, watch the timeline complete, see the appointment and reminders, log in as staff, approve an escalation, and read the audit trail and checkpoint history.

---

## Step 10 - Reminders, follow-up jobs, and notifications

**Goal:** reminders actually fire and incomplete workflows are noticed.

**Implement** `jobs/reminders.py`:

- `run_due_reminders(db, now)`: selects reminders with `status = scheduled` and `scheduled_at <= now`; for each, calls `notifications.send` and marks the reminder `sent`; audits; returns the count.
- `detect_incomplete_workflows(db, now, older_than_hours=24)`: finds runs in `awaiting_patient` or `failed` older than the threshold; creates one `system_error` escalation per run if none is pending; audits.
- `scripts/run_jobs.py`: runs both once and prints the counts.
- Optional background loop: in the app's startup event, if `JOB_INTERVAL_SECONDS > 0`, start a daemon thread that calls both functions on that cadence with a fresh session each time. Keep it off in tests.
- Staff dashboard gets a "Run jobs now" button that calls the same functions, so the demo does not depend on the thread.

**Done when** a test creates a reminder in the past, runs the job, and asserts a `sent` reminder plus a notification row.

---

## Step 11 - Tests

**Goal:** a suite that runs with no API key and covers every rubric area.

**Setup** (`tests/conftest.py`): a temp SQLite file per session, `create_all`, seed; a `Deps` whose structured agents are `RunnableLambda` fakes returning canned Pydantic objects and whose two agent runners are fakes that call the real tools; `build_graph(fake_deps, InMemorySaver())`; `RUN_WORKFLOWS_INLINE = true`; two `TestClient` fixtures logged in as patient and staff.

**Files**

| File | Covers |
|---|---|
| `test_services.py` | booking, conflicts, idempotent booking per run, reschedule, cancel, duplicate documents, missing documents, audit rows |
| `test_auth_rbac.py` | 401 without login, 403 cross-role, ownership check on cancel |
| `test_agents.py` | each agent's output validation; the two tool-calling agents with a scripted fake chat model that emits tool calls |
| `test_safety.py` | keyword screen catches emergency phrases; diagnosis wording in a confirmation is blocked |
| `test_graph.py` | happy path end to end; failure, `failed` status, retry to completion; document-only plan; cancel inside the sensitive window reaches `action_review`; persistence across a new graph instance with `SqliteSaver` |
| `test_escalations.py` | approve resumes with staff-chosen department; reject ends the run and notifies the patient |
| `test_jobs.py` | due reminders fire; stale runs escalate |
| `test_ui.py` | pages render 200 with real rows from the seeded database |

**Done when** `pytest -q` passes locally without `ANTHROPIC_API_KEY` set.

---

## Step 12 - README, submission files, CI

**Goal:** everything the automated checks and the human judges need.

- **README.md** sections: what AgentCare does and what it deliberately does not do (no diagnosis, prescription, dosage); a diagram of the LangGraph graph (render it with `graph.get_graph().draw_mermaid()` and paste the Mermaid block); the agent table from Step 6; the tool list from Step 4; data model summary; the two persistence layers and how they stay in sync; safety and escalation rules; role enforcement; setup (`python -m venv`, install, copy `.env.example`, `python scripts/init_db.py`, `uvicorn agentcare.main:app`); seeded logins; how to run tests; optional LangSmith tracing; known limitations (notifications are simulated, single-node background jobs).
- **`.env.example`** kept in sync with `config.py`. Never commit `.env`.
- **CI:** download the workflow file from the hackathon URL into `.github/workflows/agentcare-checks.yml`, add `SUBMISSION_TOKEN` as a repository secret, push, and confirm the Actions run passes "code compiles" and "LLM client listed". Do this early so every later push is checked.
- Before pushing, grep the repository for `sk-ant`, `lsv2_`, `api_key=`, and any real-looking email or phone. The seed data must be obviously synthetic.

**Done when** a fresh clone on another machine reaches a working app by following only the README.

---

## Step 13 - Demo script and final rubric check

**Goal:** a rehearsed path that shows every scored area in under five minutes.

**Scenarios** (all supported by the seed data)

1. Happy path: patient one submits "I need a cardiology follow-up next week and want to attach my old ECG" with a PDF. Show the timeline completing, the appointment, the classified document, the missing `blood_report` notice, the reminders, and the checkpoint history on the staff detail page.
2. Duplicate document: upload the same PDF again. Show the rejection message and the audit row.
3. Emergency: submit "I have crushing chest pain right now". Show the immediate block, the emergency guidance, and the escalation in the staff queue.
4. Ambiguous routing plus approval: submit "I need to see someone about my results". Show the `low_confidence` escalation, approve as staff with a department, and watch the run resume and finish.
5. Sensitive action: cancel an appointment that is within 24 hours. Show the approval requirement and the audit trail.

**Rubric checklist before submitting**

- [ ] Three or more agents with separate prompt files, schemas, and tools (six here, two with real tool loops)
- [ ] Coordinator is a LangGraph graph with state checkpointed after every node and mirrored to SQL
- [ ] Three or more tools with real logic invoked by the workflow (eight services, seven `@tool` wrappers)
- [ ] SQL database with every entity from the data model
- [ ] Role checks in routes and in services, with tests
- [ ] Escalation records created from interrupts; staff approval resumes the graph; all persisted
- [ ] Audit events for every tool call and every agent decision
- [ ] Failure marks the run failed; retry resumes the failed node without duplicate side effects
- [ ] Settings from environment only; `.env.example` present; `.env` ignored
- [ ] Synthetic seed data only
- [ ] Confirmation rendered from database rows, not from model text alone
- [ ] Tests pass without an API key
- [ ] README explains setup, architecture, the graph, agents, and tools
- [ ] CI workflow green with the submission token

---

## Order of work at a glance

| Order | Step | Share of effort |
|---|---|---|
| 1 | Skeleton and config | 5% |
| 2 | Models and seed | 10% |
| 3 | Auth and RBAC | 8% |
| 4 | Tools | 15% |
| 5 | LLM factory | 3% |
| 6 | Agents | 17% |
| 7 | Graph and runner | 17% |
| 8 | Escalations | 5% |
| 9 | UI | 10% |
| 10 | Jobs | 3% |
| 11 | Tests | 5% (written alongside each step, finished here) |
| 12 | README and CI | 2% |
| 13 | Demo | rehearsal only |

Steps 1 through 7 are the scoring core. Get a request flowing end to end through the graph with a plain form before spending time on pages or extensions.
