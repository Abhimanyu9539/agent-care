# AgentCare

LangGraph multi-agent patient-care coordination assistant. A patient writes a request in their own words; a team of agents checks it is safe, works out what they want and which department should handle it, and hands anything medical, unclear or broken to hospital staff.

## How a request is handled

Every request runs as a LangGraph workflow in the background, right after the patient sends it (`app/graph/`):

1. **Safety** (`app/agents/safety/`). Word rules catch obvious emergencies and medical-advice questions first. If no rule matches, the LLM reads the request. An emergency shows the patient a "Call 112" message and opens an URGENT case for staff. A question about medicines, doses or a diagnosis is politely declined. Only an ordinary request goes on.
2. **Coordinator** (`app/agents/coordinator/`). Asks the LLM once what the patient wants (book, reschedule, cancel, documents or status) and which agents should handle it. It then hands the request to each agent in turn; every agent reports back to it, and it finishes when the plan is done.
3. **Routing** (`app/agents/routing/`). The LLM calls two tools, `list_departments` and `get_patient_history`, and picks a department and visit type. Code checks the answer: an unknown department or low confidence goes to staff, and a follow-up for a department the patient has never visited becomes a new visit.

Rules the agents always follow:

- Personal details (emails, long numbers, the patient's name) are masked before any text goes to the LLM, and the tools never see a patient id.
- Every LLM answer fills in a fixed form (a Pydantic model), so nothing else gets through.
- If an LLM call fails, the request goes to staff instead of guessing. The LLM client itself retries a failed call twice (`LLM_MAX_RETRIES`).
- Each step is saved with what it decided, the model, prompt version and tokens, and any tool calls, but never the patient's words.

To see the graph as a picture:

```
python -m app.graph.builder
```

It writes `app/graph/workflow_graph.png`, drawn by the mermaid.ink web service (only the node names are sent).

## Staff console

Staff (for example `rhea.menon@example.com`) see:

- **Escalations**: open cases the agents handed to a person, most urgent first.
- **Requests**: every request, newest first, with its intent and how safety and routing decided it.
- **Request timeline** (click a WR number): every step the agents ran.

### Failures and retry

If something unexpected breaks a request (a bug, the database dropping out), it is marked **FAILED** with the error's type, never its text. A request that has been RUNNING with no progress for 10 minutes, for example because the server restarted mid-run, shows as **Stuck**. On the timeline of either, staff can press **Retry from the start**: the whole workflow runs again, and the earlier attempt's steps stay as history.

## Database setup

The schema lives in `app/db/tables/` as plain SQL, one file per table. The number prefix is the order they run in (enums first).

1. Start Postgres:

   ```
   docker compose up -d db
   ```

2. Create the tables.

   PowerShell:

   ```
   Get-Content app/db/tables/*.sql | docker exec -i agent-care-db-1 psql -U agentcare -d agentcare -v ON_ERROR_STOP=1 --single-transaction
   ```

   Git Bash / Linux / macOS:

   ```
   cat app/db/tables/*.sql | docker exec -i agent-care-db-1 psql -U agentcare -d agentcare -v ON_ERROR_STOP=1 --single-transaction
   ```

   It runs in one transaction, so it either creates everything or nothing. Run it once on an empty database.

3. Optional: load the sample data from `app/db/seed/` (same layout, one file per table). Run this after step 2, once:

   ```
   Get-Content app/db/seed/*.sql | docker exec -i agent-care-db-1 psql -U agentcare -d agentcare -v ON_ERROR_STOP=1 --single-transaction
   ```

   The sample data matches the people and IDs in the UI design mockups. Dates are counted from the day you load it. Every login uses the password `password123`:

   | Email | Role |
   |---|---|
   | `admin@example.com` | admin |
   | `rhea.menon@example.com` | staff |
   | `ananya.rao@example.com` and seven other patients (see `app/db/seed/01_users.sql`) | patient |

To start over, `docker compose down -v` deletes the database volume.

## Run the app

The backend is a FastAPI JSON API under `/api/`. The frontend is a React app in `frontend/`, built with Vite. It needs Node 22 or newer.

1. Copy `.env.example` to `.env` and set `SECRET_KEY` (the file shows how to generate one) and `OPEN_ROUTER_API_KEY` (from https://openrouter.ai/keys). Without the key the app still runs, but every request that needs the LLM goes to staff. Check the key works with `python -m scripts.ask_llm`.
2. With the database running and the tables created, start the backend:

   ```
   uvicorn app.main:app --reload
   ```

3. In a second terminal, start the frontend:

   ```
   cd frontend
   npm install
   npm run dev
   ```

4. Open http://localhost:5173 and log in with a sample account, or register a new patient. Vite passes every `/api` request on to the backend on port 8000.

To run it the way production does, build the frontend once with `npm run build` in `frontend/`. The backend then serves the built app itself at http://127.0.0.1:8000, so only uvicorn needs to run.

## Tests

The tests use the real Postgres database, so start it first (`docker compose up -d db`), then run `pytest`.

They never call the real LLM and need no API key: a fake LLM (`fake_llm` in `tests/conftest.py`) gives fixed answers, and tests without it run with no key, which is how the "LLM is down" path is tested. Test accounts use emails like `test-…@example.com`; they and everything they create are deleted after each test.

## Troubleshooting

- **`OPENSSL_Uplink: no OPENSSL_Applink` on Windows.** The `SSLKEYLOGFILE` environment variable points somewhere Python can't write. Remove it for the session (PowerShell: `Remove-Item Env:SSLKEYLOGFILE`).
- **`CERTIFICATE_VERIFY_FAILED` when drawing the graph.** Antivirus HTTPS scanning (such as Norton Web/Mail Shield) re-signs web traffic with its own certificate, which Python's `requests` library doesn't trust. Switch the scanning off for Python, or paste the Mermaid text from `GRAPH.get_graph().draw_mermaid()` into https://mermaid.live.
- **Tests or the app seem to hang.** The database container has probably stopped: `docker compose up -d db`.
