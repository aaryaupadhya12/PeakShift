"""Configuration helpers for database connections.

Provides functions to resolve the DB path and obtain sqlite3 connections
that use Row factories. Uses environment variables TEST_DB_PATH and
TEST_MODE to allow test overrides.
"""

import os
import sqlite3


def get_db_path():
    """Resolve the database path based on environment variables.

    - If TEST_DB_PATH is set, use that path (useful for CI temporary files)
    - If TEST_MODE is set, use an in-memory SQLite database
    - Otherwise use the persistent volunteer.db located next to this module
    """
    test_db_path = os.environ.get("TEST_DB_PATH")
    if test_db_path:
        return test_db_path

    # Use a shared in-memory URI when TEST_MODE is enabled so multiple
    # connections in the same process can see the same in-memory DB.
    if os.environ.get("TEST_MODE"):
        return "file:shared_mem_db?mode=memory&cache=shared"

    return os.path.join(os.path.dirname(__file__), "volunteer.db")


def get_connection():
    """Return a sqlite3.Connection configured with a Row factory.

    Uses get_db_path() so tests can override via environment.
    """
    db_path = get_db_path()
    # If db_path is an SQLite URI (starts with file:), enable uri=True
    uri = True if isinstance(db_path, str) and db_path.startswith("file:") else False
    conn = sqlite3.connect(db_path, check_same_thread=False, uri=uri)
    conn.row_factory = sqlite3.Row
    return conn