""" FastAPI application: routes and template setup """
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from bloodtracker.config import DB_PATH, PACKAGE_DIR
from bloodtracker.db import connect, migrate

templates = Jinja2Templates(directory=PACKAGE_DIR / "templates")


def create_app(db_path: Path | str = DB_PATH) -> FastAPI:
    """ Build the app (a factory, so tests can create isolated instances,
        each with its own throwaway database) """
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True) # e.g. create data/ on first run
    conn = connect(db_path)
    try:
        migrate(conn) # A fresh install builds its own tables; an existing one gets any new migrations
    finally:
        conn.close()

    app = FastAPI(title="BloodTestTracker")
    app.state.db_path = db_path # Routes added in later steps open connections from this
    app.mount("/static", StaticFiles(directory=PACKAGE_DIR / "static"), name="static")

    @app.get("/", response_class=HTMLResponse)
    def index(request: Request):
        return templates.TemplateResponse(request, "index.html")

    return app
