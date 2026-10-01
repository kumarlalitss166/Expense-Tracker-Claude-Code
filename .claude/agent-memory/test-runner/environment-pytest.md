---
name: environment-pytest
description: No venv on this machine — use `py -m pytest` from repo root; system Python 3.13 has the pinned deps
metadata:
  type: reference
---

There is **no `venv/` directory** in this repo checkout, despite CLAUDE.md describing one. Do not try to activate `.\venv\Scripts\Activate.ps1`.

Working invocation (Windows, from repository root):

```
py -m pytest -q
py -m pytest tests/<file>.py -v
```

`py` resolves to system Python 3.13.15, which already has the pinned set (pytest 8.3.5, pytest-flask 1.3.0, Flask 3.1.3, Werkzeug 3.1.6). No install step needed. `py -m pytest` puts the repo root on `sys.path`, which bare `pytest` does not — prefer it.

**How to apply:** skip the venv-activation step in the standard runbook; go straight to `py -m pytest`. If imports of `app` or `database` fail, check `sys.path` / cwd before assuming a missing dependency.
