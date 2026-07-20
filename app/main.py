"""FastAPI application factory for AgentCare."""

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from starlette.middleware.sessions import SessionMiddleware

from app.api.patient import router as patient_router
from app.api.staff import router as staff_router
from app.auth.routes import router as auth_router
from app.config import Settings, get_settings
from app.db.session import make_engine, make_session_factory

# The React app's production build (`npm run build` in frontend/).
FRONTEND_DIST = Path(__file__).parent.parent / "frontend" / "dist"


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build the FastAPI app. Tests may pass their own settings."""
    settings = settings or get_settings()

    app = FastAPI(title="AgentCare")
    app.state.settings = settings
    # Tables are created from app/db/tables/*.sql (see README), not at startup.
    app.state.engine = make_engine(settings.database_url)
    app.state.session_factory = make_session_factory(app.state.engine)

    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.secret_key.get_secret_value(),
        same_site="lax",
        https_only=settings.app_env == "production",
    )
    app.include_router(auth_router)
    app.include_router(patient_router)
    app.include_router(staff_router)

    @app.get("/health")
    def health() -> JSONResponse:
        """Report whether the app is up and the database answers a query."""
        try:
            with app.state.engine.connect() as connection:
                connection.execute(text("SELECT 1"))
        except SQLAlchemyError:
            return JSONResponse({"status": "error", "database": "down"}, status_code=503)
        return JSONResponse({"status": "ok", "database": "ok"})

    if FRONTEND_DIST.exists():
        app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

        # Registered last, so every API route above wins.
        @app.get("/{path:path}", include_in_schema=False)
        def frontend(path: str) -> FileResponse:
            """Every page is the React app; its router picks what to show."""
            if path.startswith("api/"):
                raise HTTPException(status_code=404)
            return FileResponse(FRONTEND_DIST / "index.html")

    return app


app = create_app()
