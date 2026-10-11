""" FastAPI application: routes and template setup """
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from bloodtracker.config import PACKAGE_DIR

templates = Jinja2Templates(directory=PACKAGE_DIR / "templates")


def create_app() -> FastAPI:
    """ Build the app (a factory, so tests can create isolated instances) """
    app = FastAPI(title="BloodTestTracker")
    app.mount("/static", StaticFiles(directory=PACKAGE_DIR / "static"), name="static")

    @app.get("/", response_class=HTMLResponse)
    def index(request: Request):
        return templates.TemplateResponse(request, "index.html")

    return app
