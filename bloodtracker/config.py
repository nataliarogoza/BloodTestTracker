""" Paths and settings. The database location can be overridden with BLOODTRACKER_DB """
import os
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = PACKAGE_DIR.parent
DB_PATH = Path(os.environ.get("BLOODTRACKER_DB", PROJECT_DIR / "data" / "tracker.db"))

HOST = "127.0.0.1" # Local only - health data is never exposed to the network
PORT = int(os.environ.get("BLOODTRACKER_PORT", "8000"))
