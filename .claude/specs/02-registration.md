# Spec: Registration

## Overview

Implement user registration for Spendly. The registration page and form already exist as a UI shell; this step wires the `POST /register` handler so a visitor can create a real account. The handler validates input, hashes the password with Werkzeug, and inserts a row into the `users` table via the existing `get_db()` helper. This is the first auth step and unlocks login, logout, and every logged-in expense feature later on the roadmap.

## Depends on

- Step 1 — Database Setup (complete): `users` table, `get_db()`, `init_db()` in `database/db.py`

## Routes

- `GET /register` — render registration form (already exists) — public
- `POST /register` — validate and create account, then redirect to `/login` — public

No other routes change. `/logout`, `/profile`, and expense placeholders stay as stubs.

## Database changes

No database changes. `users` already has everything needed (`id`, `name`, `email`, `password_hash`, `created_at`, unique email).

## Templates

- **Create:** none
- **Modify:** none. `templates/register.html` already posts to `/register` and renders `{{ error }}`. Accept that a failed submit clears the form fields (no repopulation). Never pre-fill the password field.

## Files to change

- `app.py` — POST handling on `/register`, validation, insert, redirect

Imports `app.py` will need:

- `sqlite3` — for `IntegrityError` only (UNIQUE race fallback)
- `redirect`, `render_template`, `request`, `url_for` from `flask`
- `generate_password_hash` from `werkzeug.security`
- `get_db` (already imported), `init_db`, `seed_db` from `database.db`

## Files to create

- None

## New dependencies

No new dependencies.

## Rules for implementation

- No SQLAlchemy or ORMs
- Parameterised queries only — never string-format SQL
- Passwords hashed with werkzeug (`generate_password_hash`)
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- Use `get_db()` from `database/db.py`; do not open sqlite3 connections by hand
- Strip `name` and `email`; lowercase `email`. Never strip `password`
- Reject whitespace-only name/email and emails without a basic `@` + domain shape (require a non-empty local part, exactly one `@`, and a domain that contains `.`, does not start or end with `.`, and has no `..`)
- Password minimum length is 8 characters (matches the form placeholder). Do not enforce this minimum on login (Step 3) — the seeded demo password `demo123` is only 7 characters
- Detect duplicate email by catching `sqlite3.IntegrityError` on INSERT; also pre-check with `SELECT` first for a friendly message without attempting an insert
- Always close the connection in `try/finally`, matching `database/db.py`
- On any validation failure, re-render `register.html` with `error` set and status `400` — do not redirect
- On success, commit and redirect to `/login` (login is Step 3; do not implement sessions here)
- Do not log or print the plaintext password
- No CSRF protection — acceptable for this learning project

## Definition of done

- [x] Submitting the form with valid name, email, and password (8+ chars) creates a row in `users` and lands on `/login`
- [x] The stored password is a Werkzeug hash, never plaintext
- [x] `created_at` is populated (column default or explicit value)
- [x] Submitting a duplicate email shows an error on the registration page and does not insert a second row
- [x] Registering `Demo@Spendly.com` (mixed case) is rejected as a duplicate of the seed user
- [x] Submitting a password shorter than 8 characters shows an error and does not insert
- [x] Submitting empty name or email shows an error and does not insert
- [x] Whitespace-only name or email shows an error and does not insert
- [x] Email without a basic `@` + domain shape shows an error and does not insert
- [x] Validation errors respond with HTTP 400
- [x] Email is stored lowercase and trimmed
- [x] Refreshing after a successful submit does not create a duplicate account for that email
- [x] App starts with no errors and existing routes (`/`, `/login`, `/terms`) still work

## Notes for later steps

- Step 3 (login/logout) will need `app.secret_key` and sessions/flash — a "registered successfully" message on `/login` belongs there, not here
- Login must not enforce the 8-character password minimum, or `demo@spendly.com` / `demo123` cannot sign in
