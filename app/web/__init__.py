"""Server-rendered pages. `templates` renders the Jinja files in web/templates/."""

from pathlib import Path

from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory=Path(__file__).parent / "templates")
