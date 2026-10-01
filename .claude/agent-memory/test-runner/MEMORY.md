# Test-runner memory index

- [Environment / pytest invocation](environment-pytest.md) — no venv on this machine; use `py -m pytest` from repo root (system Python 3.13 has pinned deps)
- [DB isolation guard](isolation-guard.md) — root `conftest.py` repoints `DB_PATH` at import time; verify before every run
