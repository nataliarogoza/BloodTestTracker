""" FastAPI application: pages, HTMX routes and security checks """
import datetime
import sqlite3
from pathlib import Path
from typing import Annotated
from urllib.parse import urlsplit

from fastapi import Depends, FastAPI, Form, Request
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import HTMLResponse, PlainTextResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from bloodtracker import services
from bloodtracker.config import BACKUP_DIR, DB_PATH, PACKAGE_DIR
from bloodtracker.db import KEEP_STARTUP_BACKUPS, backup_database, backup_on_startup, connect, list_backups, migrate
from bloodtracker.services import NotFoundError, ValidationError, format_exact

ALLOWED_HOSTS = ["127.0.0.1", "localhost"]


def format_value(result) -> str:
    """ How a result's value is shown; text values are kept as is ("<0.5") """
    if result["value"] is None:
        return result["value_text"] or ""
    return format_exact(result["value"])


def format_rounded(number: float) -> str:
    """ A calculated number (average, spread), rounded for reading: 61.2333 -> "61.23",
        small numbers keep 3 significant digits so they don't become 0: 0.00412 -> "0.00412" """
    if number != 0 and abs(number) < 1:
        return f"{number:.3g}"
    return f"{number:.2f}".rstrip("0").rstrip(".")


templates = Jinja2Templates(directory=PACKAGE_DIR / "templates")
templates.env.filters["value"] = format_value
templates.env.filters["exact"] = format_exact
templates.env.filters["rounded"] = format_rounded


def get_conn(request: Request):
    """ One database connection per request, closed when the request is done """
    conn = connect(request.app.state.db_path)
    try:
        yield conn
    finally:
        conn.close()


Conn = Annotated[sqlite3.Connection, Depends(get_conn)]


def create_app(db_path: Path | str = DB_PATH, backup_dir: Path | str = BACKUP_DIR) -> FastAPI:
    """ Build the app (a factory, so tests can create isolated instances,
        each with its own throwaway database and backup folder) """
    db_path, backup_dir = Path(db_path), Path(backup_dir)
    db_path.parent.mkdir(parents=True, exist_ok=True) # e.g. create data/ on first run
    is_new_database = not db_path.exists()
    backup_problem = None
    conn = connect(db_path)
    try:
        if not is_new_database: # A brand-new database has nothing to back up yet
            try:
                backup_on_startup(conn, db_path, backup_dir)
            except (OSError, sqlite3.Error) as error: # e.g. disk full: still start, but say so on the Data page
                backup_problem = f"The automatic backup when the app started failed: {error}"
                print(f"WARNING: {backup_problem}")
        # A fresh install builds its own tables; an existing one gets any new migrations,
        # after a safety backup of how it was
        migrate(conn, backup_dir=backup_dir)
    finally:
        conn.close()

    # No /docs page: it's for developers, and it would load its scripts from the internet
    app = FastAPI(title="BloodTestTracker", docs_url=None, redoc_url=None, openapi_url=None)
    app.state.db_path = db_path
    app.state.backup_dir = backup_dir
    app.state.backup_problem = backup_problem
    app.mount("/static", StaticFiles(directory=PACKAGE_DIR / "static"), name="static")

    # Security 1: only answer requests addressed to this computer by name. Blocks "DNS rebinding",
    # where a website makes your browser talk to 127.0.0.1 under the website's own name.
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=ALLOWED_HOSTS)

    @app.middleware("http")
    async def refuse_cross_site_changes(request: Request, call_next):
        """ Security 2 (CSRF protection): another website open in your browser could otherwise
            send "add" or "delete" requests here. Browsers say where a request comes from
            (Origin / Sec-Fetch-Site), so changes are only accepted from this app's own pages. """
        if request.method not in ("GET", "HEAD", "OPTIONS"):
            origin = request.headers.get("origin")
            cross_site = request.headers.get("sec-fetch-site") == "cross-site"
            if cross_site or (origin is not None and urlsplit(origin).netloc != request.headers.get("host")):
                return PlainTextResponse("Refused: this request didn't come from BloodTestTracker.", status_code=403)
        return await call_next(request)

    def render(request, template, context, headers=None):
        return templates.TemplateResponse(request, template, context, headers=headers)

    def form_context(conn, **extra):
        """ What every form needs: the grouped test list, unit suggestions, today's date """
        groups = {}
        for test in services.list_tests(conn):
            groups.setdefault(test["category"] or "Other", []).append(test)
        return {"test_groups": groups, "units": services.list_units(conn),
                "today": datetime.date.today().isoformat(), **extra}

    def blank_form(**fields):
        return {"test_id": "", "date": datetime.date.today().isoformat(), "value": "", "unit": "",
                "error": None, "message": None, **fields}

    def to_int(text: str) -> int:
        try:
            return int(text)
        except (TypeError, ValueError):
            return 0 # No test has id 0, so this becomes "Please choose a test"

    @app.get("/", response_class=HTMLResponse)
    def index(request: Request, conn: Conn):
        return render(request, "index.html", form_context(conn, form=blank_form(), results=services.list_results(conn)))

    @app.post("/results", response_class=HTMLResponse)
    def add_result(request: Request, conn: Conn, test_id: str = Form(""), date: str = Form(""),
                   value: str = Form(""), unit: str = Form("")):
        try:
            new_id = services.add_result(conn, to_int(test_id), date, value, unit)
        except ValidationError as error:
            form = blank_form(test_id=test_id, date=date, value=value, unit=unit, error=str(error))
            return render(request, "partials/add_form.html", form_context(conn, form=form))

        saved = services.get_result(conn, new_id)
        # Keep test, date and unit for quick entry of the next result from the same visit
        form = blank_form(test_id=test_id, date=saved["date"], unit=unit, focus_value=True,
                          message=f"Added {saved['test_name']}: {format_value(saved)} {saved['unit'] or ''} on {saved['date']}")
        return render(request, "responses/after_add.html",
                      form_context(conn, form=form, results=services.list_results(conn)))

    @app.get("/results/{result_id}", response_class=HTMLResponse)
    def show_row(request: Request, conn: Conn, result_id: int):
        try:
            return render(request, "partials/row.html", {"r": services.get_result(conn, result_id)})
        except NotFoundError:
            return reload_page()

    @app.get("/results/{result_id}/edit", response_class=HTMLResponse)
    def edit_row(request: Request, conn: Conn, result_id: int):
        try:
            r = services.get_result(conn, result_id)
        except NotFoundError:
            return reload_page()
        form = blank_form(test_id=str(r["test_id"]), date=r["date"], value=format_value(r), unit=r["unit"] or "")
        return render(request, "partials/edit_row.html", form_context(conn, r=r, form=form))

    @app.put("/results/{result_id}", response_class=HTMLResponse)
    def save_row(request: Request, conn: Conn, result_id: int, test_id: str = Form(""),
                 date: str = Form(""), value: str = Form(""), unit: str = Form("")):
        try:
            services.update_result(conn, result_id, to_int(test_id), date, value, unit)
        except NotFoundError:
            return reload_page()
        except ValidationError as error:
            r = {"id": result_id}
            form = blank_form(test_id=test_id, date=date, value=value, unit=unit, error=str(error))
            return render(request, "partials/edit_row.html", form_context(conn, r=r, form=form))
        # Success: redraw the whole table, since a changed date can move the row
        return render(request, "partials/rows.html", {"results": services.list_results(conn)},
                      headers={"HX-Retarget": "#results-body", "HX-Reswap": "innerHTML"})

    @app.delete("/results/{result_id}", response_class=HTMLResponse)
    def delete_row(request: Request, conn: Conn, result_id: int):
        try:
            services.delete_result(conn, result_id)
        except NotFoundError:
            pass # Already gone (e.g. deleted in another tab) - removing the row is still right
        return render(request, "responses/after_delete.html", {"count": len(services.list_results(conn))})

    def chart_context(conn, test_param: str) -> dict:
        """ Everything the charts page shows for the chosen test (if any) """
        groups = {}
        for t in services.list_tests_with_results(conn):
            groups.setdefault(t["category"] or "Other", []).append(t)
        context = {"chart_groups": groups, "selected_id": None, "test": None, "error": None}
        if not test_param:
            return context
        try:
            test = services.get_test(conn, int(test_param))
        except (ValueError, NotFoundError):
            return context | {"error": "That test wasn't found - choose one from the list."}

        history = services.test_history(conn, test["id"])
        series = services.series_by_unit(history)
        return context | {
            "selected_id": test["id"],
            "test": test,
            "history": list(reversed(history)), # Table: newest first, like the results page
            "series": series,
            "text_count": sum(1 for r in history if r["value"] is None),
            "chart_data": {"series": [{"unit": s.unit, "dates": s.dates, "values": s.values} for s in series]},
        }

    @app.get("/charts", response_class=HTMLResponse)
    def charts(request: Request, conn: Conn, test: str = ""):
        # HTMX asks for just the panel when you pick a test; a normal visit (or a refresh,
        # or going back in history) gets the whole page
        panel_only = (request.headers.get("hx-request") == "true"
                      and request.headers.get("hx-history-restore-request") != "true")
        template = "partials/chart_panel.html" if panel_only else "charts.html"
        # Vary: tells the browser the reply depends on that header, so it never shows a cached
        # panel-only reply as if it were the whole page
        return render(request, template, chart_context(conn, test), headers={"Vary": "HX-Request"})

    def backup_kind(name: str) -> str:
        if "_startup" in name:
            return "Automatic"
        if "_before-" in name:
            return "Before upgrade"
        return "Manual"

    def backups_context(message=None, error=None):
        backups = [{"name": p.name, "kind": backup_kind(p.name), "size_kb": max(1, round(p.stat().st_size / 1024)),
                    "created": datetime.datetime.fromtimestamp(p.stat().st_mtime).strftime("%Y-%m-%d %H:%M")}
                   for p in list_backups(backup_dir)]
        return {"backups": backups, "backup_dir": backup_dir, "db_path": db_path, "keep": KEEP_STARTUP_BACKUPS,
                "message": message, "error": error or app.state.backup_problem}

    @app.get("/data", response_class=HTMLResponse)
    def data_page(request: Request, conn: Conn):
        result_count = conn.execute("SELECT count(*) FROM results").fetchone()[0]
        return render(request, "data.html", backups_context() | {"result_count": result_count})

    @app.get("/export/results.csv")
    def export_csv(conn: Conn):
        filename = f"blood_test_results_{datetime.date.today().isoformat()}.csv"
        return Response(services.results_csv(conn), media_type="text/csv; charset=utf-8",
                        headers={"Content-Disposition": f'attachment; filename="{filename}"'}) # Download, not show

    @app.post("/backups", response_class=HTMLResponse)
    def create_backup(request: Request, conn: Conn):
        try:
            path = backup_database(conn, backup_dir)
        except OSError as error: # e.g. disk full, no permission
            return render(request, "partials/backups.html", backups_context(error=f"Backup failed: {error}"))
        return render(request, "partials/backups.html", backups_context(message=f"Saved {path.name}"))

    def reload_page():
        """ The result vanished (e.g. deleted in another tab): ask HTMX to reload the page """
        return HTMLResponse("", headers={"HX-Refresh": "true"})

    return app
