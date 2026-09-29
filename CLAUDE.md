# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

**Spendly** is a Flask personal expense tracker built as a step-by-step campus-x learning project. Users will register/sign in, log expenses (amount, category, date, description), and view spending by category and date range. Currency/UI copy is rupee-focused (“Track every rupee”).

Current state: marketing/auth UI shell is in place. SQLite helpers, session auth, and expense CRUD are stubs for later steps.

## Commands

Windows uses the `py` launcher in this environment.

```bash
# Create / activate venv (from repo root)
py -m venv venv
# PowerShell:
.\venv\Scripts\Activate.ps1
# Git Bash / cmd:
# source venv/Scripts/activate   OR   venv\Scripts\activate.bat

# Install deps
pip install -r requirements.txt

# Run the app (http://0.0.0.0:5000 — debug on)
py app.py

# Tests (pytest + pytest-flask are pinned; no test suite yet)
pytest
pytest path/to/test_file.py
pytest path/to/test_file.py::test_name
pytest -k "keyword"
```

There is no separate lint/build step. Do not commit `venv/`, `expense_tracker.db`, or `.env` (see `.gitignore`).

## Architecture

Single-process Flask app — no blueprints, no ORM, no frontend framework.

| Path | Role |
|------|------|
| `app.py` | Flask app factory-by-convention: creates `app`, defines all routes, `app.run(debug=True, host="0.0.0.0", port=5000)` |
| `database/db.py` | Stub for Step 1 — implement `get_db()`, `init_db()`, `seed_db()` with stdlib `sqlite3`; DB file `expense_tracker.db` |
| `templates/` | Jinja2 pages extending `base.html` (`{% block content %}`, optional `head` / `scripts`) |
| `static/css/style.css` | Global design tokens (`:root` CSS variables) and page styles |
| `static/js/main.js` | Vanilla JS only (no npm/bundler) — currently the landing “See how it works” YouTube modal |
| `docs/` | Session notes, prompts, and UI mockups — not runtime code |
| `requirements.txt` | Pinned: Flask 3.1.3, Werkzeug 3.1.6, pytest 8.3.5, pytest-flask 1.3.0 |

### Request flow

1. Browser hits a route in `app.py`.
2. Implemented routes (`/`, `/register`, `/login`, `/terms`) `render_template(...)`.
3. Placeholder routes (`/logout`, `/profile`, `/expenses/...`) return plain strings for later steps.
4. Templates pull assets via `url_for('static', ...)`.

### Auth / forms gap

`login.html` and `register.html` POST to `/login` and `/register`, but those routes only handle GET and render templates — POST handlers, sessions, password hashing, and DB persistence are not implemented yet.

### UI conventions

- Brand: **Spendly**; fonts DM Serif Display + DM Sans (Google Fonts in `base.html`).
- Design references live under `docs/UI Design Templates/`.
- Prefer vanilla JS in `static/js/`; do not introduce a JS framework unless explicitly asked.
- Footer Privacy Policy link in `base.html` is still `#` (Terms is wired to `url_for('terms')`).

### Learning-step placeholders in `app.py`

Comments map unfinished routes to curriculum steps (logout → Step 3, profile → Step 4, expense add/edit/delete → Steps 7–9). Prefer filling those in place over inventing a new app layout unless the task asks for a refactor.
