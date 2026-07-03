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

## Tests

The tests use the real Postgres database, so start it first (`docker compose up -d db`), then run `pytest`.
