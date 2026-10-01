"""Pytest bootstrap — keep every test off the real expense_tracker.db.

`app.py` calls `init_db()` / `seed_db()` at import time, so `database.db.DB_PATH`
MUST be repointed at a temporary file before anything imports `app`.
This module-level redirect is the safety guard the test pipeline requires.
"""

import sys
import tempfile
from pathlib import Path

import pytest

# Project root on sys.path so `import app` / `import database.db` work from tests/
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# --- DB isolation: must run before `import app` in any test module --- #
import database.db as _db  # noqa: E402

_TMPDIR = tempfile.mkdtemp(prefix="spendly-pytest-")
_db.DB_PATH = Path(_TMPDIR) / "expense_tracker.db"


@pytest.fixture()
def app():
    """The Flask app, with an isolated temp DB already initialised."""
    import app as app_module

    return app_module.app


@pytest.fixture()
def client(app):
    """Flask test client bound to the isolated app."""
    app.config["TESTING"] = True
    return app.test_client()


@pytest.fixture()
def db_conn(app):
    """Open connection to the temp DB (caller closes via the fixture teardown)."""
    conn = _db.get_db()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()
