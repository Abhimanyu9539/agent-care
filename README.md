# AgentCare

LangGraph multi-agent patient-care coordination assistant. Full documentation is in progress; see `IMPLEMENTATION_PLAN.md` for the build plan.

## Database setup (migration step)

1. Copy `.env.example` to `.env` and set `SECRET_KEY`.
2. Create the application tables and load synthetic demo data:

   ```
   python scripts/init_db.py
   ```

   This runs `Base.metadata.create_all` against `DATABASE_URL`, then seeds. It is safe to run again: seeding is skipped once departments exist.

3. LangGraph checkpoint tables live in a separate SQLite file (`CHECKPOINT_DB`) and are created by `SqliteSaver.setup()` when the app starts.

### Seeded data

All seeded data is synthetic.

- Departments: Cardiology, Orthopaedics, Dermatology, General Medicine, with two doctors each.
- Slots: every weekday for the next 21 days, 09:00 to 17:00 **UTC** in 30-minute blocks. A few slots are pre-booked or blocked.
- Required documents: Cardiology follow-up needs `ecg` and `blood_report`. Orthopaedics new visits need `imaging`. General Medicine new visits need `id_proof`.
- Logins, all with password `password123`:

  | Email | Role | Notes |
  |---|---|---|
  | `patient1@example.com` | patient | adult; has one confirmed Cardiology appointment |
  | `patient2@example.com` | patient | under 18 (sensitive-case escalation) |
  | `patient3@example.com` | patient | senior |
  | `staff@example.com` | staff | |
