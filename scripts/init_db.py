"""Create the application tables and load synthetic demo data.

Usage (from the repository root):  python scripts/init_db.py

Safe to run repeatedly: seeding is skipped when departments already exist.
LangGraph checkpoint tables are created separately by `SqliteSaver.setup()`
when the app starts.
"""

import sys
from pathlib import Path

# The project is not pip-installed, so make `app` importable from here.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import inspect  # noqa: E402

from app.config import get_settings  # noqa: E402
from app.db.session import make_engine  # noqa: E402
from scripts.seed import init_db  # noqa: E402


def main() -> None:
    settings = get_settings()
    engine = make_engine(settings.database_url)
    try:
        created = init_db(engine)
        tables = inspect(engine).get_table_names()
    finally:
        engine.dispose()

    print("Seeded demo data" if created else "Database already seeded; nothing to do")
    print(f"{len(tables)} tables in {settings.database_url}")


if __name__ == "__main__":
    main()
