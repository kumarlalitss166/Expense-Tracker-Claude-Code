---
name: test-infra-conftest
description: Spendly pytest DB isolation (root conftest.py) and the app/client/db_conn fixtures every test must use
metadata:
  type: project
---

Repository-root `conftest.py` is the mandatory DB isolation guard for Spendly tests.

- `app.py` runs `init_db()` + `seed_db()` at **module import time**, and `database/db.py` resolves `DB_PATH` at import. So `conftest.py` must (and does) set `database.db.DB_PATH` to `Path(tempfile.mkdtemp(prefix="spendly-pytest-")) / "expense_tracker.db"` at module level, before anything imports `app`. Each pytest process gets a fresh temp dir.
- Fixtures provided: `app` (imports app module after isolation), `client` (`app.test_client()`, sets TESTING), `db_conn` (open `get_db()` connection; commits/closes on teardown).
- **Why:** plain `import app` in a test would init+seed the real `expense_tracker.db`, and profile-style tests that delete users/expenses would destroy local dev data. A function-scoped tmp_path/monkeypatch is too late — collection imports run first.
- **How to apply:** always run tests via `py -m pytest` from the repo root (root conftest is also what puts the root on sys.path). Never import `app` at test-module top level; use the fixtures or import inside test functions. `db_conn` only commits on teardown, so any seeded rows must be committed explicitly (`conn.commit()`) before issuing requests — the app opens its own connection per request. `seed_db()` runs on first `app` import, so the temp DB starts with the demo user + 8 today-dated rows: clear `expenses` then `users` in a fixture before seeding your own rows.
- Verify isolation before trusting a run: real `expense_tracker.db` mtime/size must be unchanged afterwards.
