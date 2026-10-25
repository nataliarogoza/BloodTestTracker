""" Shared test helpers ("fixtures"). pytest loads this file automatically, and any
    test that names a fixture as a parameter gets it passed in. Every test gets its
    own temporary database, so tests never touch your real data. """
import pytest
from fastapi.testclient import TestClient

from bloodtracker.app import create_app
from bloodtracker.db import connect, migrate


@pytest.fixture
def db_path(tmp_path):
    """ A path to a database file inside a fresh temporary folder """
    return tmp_path / "test.db"


@pytest.fixture
def backup_dir(tmp_path):
    """ A temporary backup folder, so tests never write into your real backups folder """
    return tmp_path / "backups"


@pytest.fixture
def conn(db_path):
    """ An open connection to a fully migrated temporary database """
    conn = connect(db_path)
    migrate(conn)
    yield conn
    conn.close()


@pytest.fixture
def client(db_path, backup_dir):
    """ A test client for an app that uses the temporary database and backup folder. It must say
        it's talking to 127.0.0.1, since the app refuses other host names (its default is "testserver"). """
    return TestClient(create_app(db_path, backup_dir), base_url="http://127.0.0.1")
