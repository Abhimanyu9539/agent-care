"""FastAPI application factory for AgentCare."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.config import Settings, get_settings
from app.db.session import make_engine, make_session_factory

STATIC_DIR = Path(__file__).parent / "web" / "static"


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build the FastAPI app. Tests may pass their own settings."""
    settings = settings or get_settings()

    app = FastAPI(title="AgentCare")
    app.state.settings = settings
    # Tables are created by scripts/init_db.py, not at startup.
    app.state.engine = make_engine(settings.database_url)
    app.state.session_factory = make_session_factory(app.state.engine)

    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.secret_key.get_secret_value(),
        same_site="lax",
        https_only=settings.app_env == "production",
    )
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
