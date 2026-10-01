# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

**Spendly** is a Flask personal expense tracker built as a step-by-step campus-x learning project. Users will register/sign in, log expenses (amount, category, date, description), and view spending by category and date range. Currency/UI copy is rupee-focused (“Track every rupee”).

Current state: landing, registration, login/logout, the profile dashboard, and profile account management (edit name/email, change password, delete account) are live. Profile expense data is served by reusable helpers and JSON endpoints (history, summary stats, category breakdown) and merged into the profile page. Expense CRUD remains stubs for later steps.

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
| `app.py` | Flask app factory-by-convention: creates `app`, defines all routes, `app.run(debug=True, host=”0.0.0.0”, port=5000)` |
| `database/db.py` | SQLite data layer — `get_db()`, `init_db()`, `seed_db()` with stdlib `sqlite3`; DB file `expense_tracker.db` |
| `templates/` | Jinja2 pages extending `base.html` (`{% block content %}`, optional `head` / `scripts`). `templates/partials/` holds includes that do **not** extend `base.html` |
| `static/css/style.css` | Global design tokens (`:root` CSS variables) and page styles |
| `static/js/main.js` | Vanilla JS only (no npm/bundler) — currently the landing “See how it works” YouTube modal |
| `docs/` | Session notes, prompts, and UI mockups — not runtime code |
| `requirements.txt` | Pinned: Flask 3.1.3, Werkzeug 3.1.6, pytest 8.3.5, pytest-flask 1.3.0 |

### Request flow

1. Browser hits a route in `app.py`.
2. `@app.before_request load_user()` attaches the signed-in user to `g.user` (and clears a stale session cookie if that user no longer exists).
3. Implemented routes (`/`, `/register`, `/login`, `/logout`, `/profile`, `/profile/edit`, `/profile/password`, `/profile/delete`, `/profile/history`, `/terms`) render templates or redirect.
4. JSON endpoints (`/api/profile/stats`, `/api/profile/breakdown`, `/api/profile/history`) return per-user expense data via `jsonify`.
5. Placeholder routes (`/expenses/...`) return plain strings for later steps.
6. Templates pull assets via `url_for('static', ...)`.

### Auth

Registration, login, logout, and `@login_required` are implemented. Sessions store `user_id` only; passwords are Werkzeug-hashed. `/profile` is the first logged-in page (identity + spending snapshot). Account management is on `/profile/edit`, `/profile/password`, and `POST /profile/delete`. Email format validation is the shared `is_valid_email()` helper used by both `/register` and `/profile/edit`.

### Profile expense data

Three helpers — `get_summary_stats()`, `get_category_breakdown()`, `get_recent_transactions()` — are the single source of truth for expense aggregates. `/profile` and the `/api/profile/*` endpoints all call them, so page and JSON numbers cannot diverge. Every expense query filters `WHERE user_id = ?`.

### Expenses gap

`/expenses/add`, `/expenses/<id>/edit`, and `/expenses/<id>/delete` are still stubs for Steps 7–9.

### UI conventions

- Brand: **Spendly**; fonts DM Serif Display + DM Sans (Google Fonts in `base.html`).
- Design references live under `docs/UI Design Templates/`.
- Prefer vanilla JS in `static/js/`; do not introduce a JS framework unless explicitly asked.
- Footer Privacy Policy link in `base.html` is still `#` (Terms is wired to `url_for('terms')`).

### Learning-step placeholders in `app.py`

Comments map unfinished routes to curriculum steps (expense add/edit/delete → Steps 7–9). Prefer filling those in place over inventing a new app layout unless the task asks for a refactor.
