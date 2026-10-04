# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

**Spendly** is a Flask personal expense tracker built as a step-by-step campus-x learning project. Users will register/sign in, log expenses (amount, category, date, description), and view spending by category and date range. Currency/UI copy is rupee-focused (“Track every rupee”).

Current state: landing, registration, login/logout, forgot-password (no OTP — learning-project reset by email + new password), the profile dashboard, and profile account management (edit name/email, change password, delete account) are live. Profile expense data is served by reusable helpers and JSON endpoints (history, summary stats, category breakdown) and merged into the profile page. Category + date-range filters (Step 6) narrow that snapshot via GET query params on the profile routes and APIs. Expense CRUD remains stubs for later steps.

The signed-in area (`/profile`, `/profile/history`, `/profile/edit`, `/profile/password`) renders through `templates/dashboard.html` — app header + left sidebar + compact footer. Public pages (landing, auth, terms) still use the marketing navbar/footer in `base.html`. The profile page is a financial dashboard: hero card, filter card, four metric tiles (total, count, average, top category), a CSS `conic-gradient` donut with category bars, recent-transactions table, and account-settings tiles.

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

# Tests (pytest + pytest-flask are pinned)
# Root conftest.py repoints database.db.DB_PATH at a temp file before
# `app` is imported, so runs never touch expense_tracker.db.
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
| `templates/` | Jinja2 pages extending `base.html` (`{% block content %}`, optional `head` / `scripts`). Signed-in pages extend `dashboard.html` instead. `templates/partials/` holds includes that do **not** extend `base.html` |
| `static/css/style.css` | Global design tokens (`:root` CSS variables) and page styles |
| `static/js/main.js` | Vanilla JS only (no npm/bundler) — currently the landing “See how it works” YouTube modal |
| `conftest.py` | Pytest bootstrap — repoints `database.db.DB_PATH` at a temp file **before** `app` is imported (DB isolation) |
| `tests/` | Pytest suites, one file per feature step (`test_<step>-<slug>.py`); `test_profile-dashboard-redesign.py` covers the dashboard UI metrics and safety contracts; `test_07-forgot-password.py` covers the reset flow |
| `docs/` | Session notes, prompts, and UI mockups — not runtime code |
| `requirements.txt` | Pinned: Flask 3.1.3, Werkzeug 3.1.6, pytest 8.3.5, pytest-flask 1.3.0 |

### Request flow

1. Browser hits a route in `app.py`.
2. `@app.before_request load_user()` attaches the signed-in user to `g.user` (and clears a stale session cookie if that user no longer exists).
3. Implemented routes (`/`, `/register`, `/login`, `/logout`, `/forgot-password`, `/profile`, `/profile/edit`, `/profile/password`, `/profile/delete`, `/profile/history`, `/terms`) render templates or redirect.
4. JSON endpoints (`/api/profile/stats`, `/api/profile/breakdown`, `/api/profile/history`) return per-user expense data via `jsonify`.
5. Placeholder routes (`/expenses/...`) return plain strings for later steps.
6. Templates pull assets via `url_for('static', ...)`.

### Auth

Registration, login, logout, and `@login_required` are implemented. Sessions store `user_id` only; passwords are Werkzeug-hashed. `/profile` is the first logged-in page (identity + spending snapshot). Account management is on `/profile/edit`, `/profile/password`, and `POST /profile/delete`. Email format validation is the shared `is_valid_email()` helper used by both `/register` and `/profile/edit`.

`/forgot-password` is the unauthenticated reset flow (email + new password + confirm, no OTP/email check). Success redirects to `/login?reset=1`, which renders a success banner via the `success=` template kwarg (the app has no `flash()`). Same validation strings as `/profile/password`, plus `"No account found with that email address."`.

### Profile expense data

Three helpers — `get_summary_stats()`, `get_category_breakdown()`, `get_recent_transactions()` — are the single source of truth for expense aggregates. `/profile` and the `/api/profile/*` endpoints all call them, so page and JSON numbers cannot diverge. Every expense query filters `WHERE user_id = ?`.

### Profile data filters (Step 6)

Optional `category`, `date_from`, `date_to` query params on `/profile`, `/profile/history`, and the three `/api/profile/*` endpoints narrow that snapshot. `parse_expense_filters()` normalises them once per request (unknown category / malformed dates ignored; reversed range → friendly error + unfiltered snapshot). `_expense_filters_sql()` returns the shared `AND …` fragment so all three helpers apply the same clause shape. UI lives in `templates/partials/filter_bar.html`.

### Expenses gap

`/expenses/add`, `/expenses/<id>/edit`, and `/expenses/<id>/delete` are still stubs for Steps 7–9.

### UI conventions

- Brand: **Spendly**; fonts DM Serif Display + DM Sans (Google Fonts in `base.html`).
- Design references live under `docs/UI Design Templates/`.
- Prefer vanilla JS in `static/js/`; do not introduce a JS framework unless explicitly asked.
- Footer Privacy Policy link is still `#` in both `base.html` and `templates/partials/app_footer.html` (Terms is wired to `url_for('terms')`).
- Core colours live in `:root` tokens; dashboard accent tints (metric icons, category badges, donut ramp in `DONUT_COLORS`) use literal hex.

### Learning-step placeholders in `app.py`

Comments map unfinished routes to curriculum steps (expense add/edit/delete → Steps 7–9). Prefer filling those in place over inventing a new app layout unless the task asks for a refactor.
