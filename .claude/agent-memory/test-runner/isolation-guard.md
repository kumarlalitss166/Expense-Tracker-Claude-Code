---
name: isolation-guard
description: DB isolation guard lives in repository-root conftest.py — repoints database.db.DB_PATH before `import app`
metadata:
  type: reference
---

The pytest DB isolation guard is the **repository-root** `conftest.py` (there is no `tests/conftest.py`). At module top level it does `import database.db as _db` then `_db.DB_PATH = Path(tempfile.mkdtemp(prefix="spendly-pytest-")) / "expense_tracker.db"` — **before** anything imports `app`.

This matters because `app.py` runs `init_db()` + `seed_db()` at import time. A fixture-level or `tests/conftest.py` guard would be too late.

Verified runtime signature: `database.db.DB_PATH` should be under `...\Temp\spendly-pytest-*\expense_tracker.db`, never the repo-root `expense_tracker.db`.

Known coupling from the single session-wide temp DB: `seed_db()` inserts `demo@spendly.com` + 8 expenses on import, and tests that insert/delete users and expenses leak into later tests. Prefer tests that seed their own deterministic data and clear `users`/`expenses` first (the Step 06 file's `clean` fixture is the good pattern).

**How to apply:** before any test run, confirm the root `conftest.py` still has the top-level repoint. If it is missing or moved, block the run and report it — never run the suite against the real DB. Record `expense_tracker.db` size/mtime before and after runs.
