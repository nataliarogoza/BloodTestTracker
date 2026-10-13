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
def conn(db_path):
    """ An open connection to a fully migrated temporary database """
    conn = connect(db_path)
    migrate(conn)
    yield conn
    conn.close()


@pytest.fixture
def client(db_path):
    """ A test client for an app that uses the temporary database """
    return TestClient(create_app(db_path))
