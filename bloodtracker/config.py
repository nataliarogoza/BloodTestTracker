""" Paths and settings. Each can be overridden with an environment variable:
    BLOODTRACKER_DB, BLOODTRACKER_BACKUP_DIR, BLOODTRACKER_PORT """
import os
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = PACKAGE_DIR.parent
DB_PATH = Path(os.environ.get("BLOODTRACKER_DB", PROJECT_DIR / "data" / "tracker.db"))
# Next to the project folder (not inside it), e.g. ~/Desktop/BloodTestTracker_backups
BACKUP_DIR = Path(os.environ.get("BLOODTRACKER_BACKUP_DIR", PROJECT_DIR.parent / f"{PROJECT_DIR.name}_backups"))

HOST = "127.0.0.1" # Local only - health data is never exposed to the network
PORT = int(os.environ.get("BLOODTRACKER_PORT", "8000"))
