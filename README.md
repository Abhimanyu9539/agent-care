# AgentCare

LangGraph multi-agent patient-care coordination assistant. Full documentation is in progress.

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

1. Copy `.env.example` to `.env` and set `SECRET_KEY` (the file shows how to generate one).
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
