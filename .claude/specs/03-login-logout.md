# Spec: Login and Logout

## Overview

Implement sign-in and sign-out for Spendly. Registration can already create accounts, but nothing keeps a user signed in. This step adds Flask sessions: `POST /login` verifies a password against the stored Werkzeug hash and stores `user_id` in the session; `GET /logout` clears the session. It also introduces `app.secret_key`, a `login_required` helper (applied to `/profile` in this step), and session-aware navigation so the UI reflects who is signed in — including on mobile.

## Depends on

- Step 1 — Database Setup (complete): `users` table, `get_db()`
- Step 2 — Registration (complete): password hashing via `generate_password_hash`, `/register` works

## Routes

- `GET /login` — render sign-in form (already exists) — public. If already signed in, redirect to `/profile`
- `POST /login` — verify email + password, set session, redirect to `/profile` — public
- `GET /logout` — clear session, redirect to `/` — public (harmless if not signed in). **No** `@login_required`
- `GET /profile` — existing stub, **now behind `@login_required`** — logged-in

`/expenses/*` placeholders stay stubs.

## Database changes

No database changes. Password verification reads `users.password_hash` only.

## Templates

- **Create:** none
- **Modify:**
  - `templates/base.html` — nav is hard-coded "Sign in" / "Get started". Make it session-aware via `is_logged_in` from a context processor. The **right-hand link must keep `class="nav-cta"`** so it survives the ≤600px rule in `static/css/style.css` (`.nav-links a:not(.nav-cta) { display: none; }`). Signed in → one link: `<a href="{{ url_for('logout') }}" class="nav-cta">Sign out</a>`.
  - `templates/login.html` — no change. Already posts to `/login` and renders `{{ error }}`. Accept that a failed submit clears the fields.

## Files to change

- `app.py` — `secret_key`, `login_required`, context processor, `POST /login`, `GET /logout`, `@login_required` on `/profile`, signed-in redirect on `GET /register`
- `templates/base.html` — session-aware nav

Imports `app.py` will need:

- `os` — for `SECRET_KEY`
- `functools.wraps` — for `login_required`
- `session` from `flask` (plus `redirect`, `render_template`, `request`, `url_for` already imported)
- `check_password_hash` from `werkzeug.security` (`generate_password_hash` is already imported)

Do **not** import `g` in this step unless you also add a `before_request` user loader.

## Files to create

- None

## New dependencies

No new dependencies.

## Rules for implementation

- No SQLAlchemy or ORMs
- Parameterised queries only — never string-format SQL
- Passwords hashed/checked with werkzeug (`generate_password_hash` / `check_password_hash`)
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- Use `get_db()` from `database/db.py`; close the connection in `try/finally`
- Set `app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-me")`
- Session key: store `user_id` (the integer `users.id`) only — never email or password
- Do **not** enforce the 8-character password minimum on login — the seeded demo password `demo123` is only 7 characters
- Strip and lowercase `email` on login the same way registration stores it. Never strip `password`
- Login failures must not reveal which field was wrong — one generic message `"Invalid email or password."`
- Empty email or password uses a specific non-revealing message: `"Please enter your email and password."`
- On validation failure, re-render `login.html` with `error` set and status `400` — do not redirect
- On success: `session.clear()` first (session fixation), then `session["user_id"] = row["id"]`, then `redirect(url_for("profile"))`
- Logout: `session.clear()` then `redirect(url_for("landing"))`. Must not error if nobody is signed in
- `login_required`: if `"user_id"` not in session → `redirect(url_for("login"))`. Wrap with `functools.wraps`
- Apply `@login_required` to the `/profile` stub in this step
- Navbar state comes from one `@app.context_processor` returning `{"is_logged_in": "user_id" in session}`
- The "Sign out" nav link uses `class="nav-cta"` so it stays visible under the 600px mobile rule
- Signed-in users visiting `GET /login` or `GET /register` are redirected to `/profile`
- Do not log or print the plaintext password
- No CSRF protection — acceptable for this learning project

## Definition of done

- [ ] Correct credentials for `demo@spendly.com` / `demo123` sign in and land on `/profile`
- [ ] Demo user can sign in even though the password is only 7 characters
- [ ] A user registered via `/register` can sign in with their password
- [ ] Wrong password shows "Invalid email or password." and does not set a session
- [ ] Unknown email shows the same generic message (no "user not found")
- [ ] Empty email or empty password shows "Please enter your email and password." and does not set a session
- [ ] Login failures respond with HTTP 400
- [ ] After sign-in, `base.html` nav shows "Sign out" instead of "Sign in" / "Get started"
- [ ] "Sign out" is visible and clickable at ≤600px width
- [ ] `/logout` clears the session and redirects to `/`
- [ ] After logout, the nav is back to "Sign in" / "Get started"
- [ ] Visiting `/logout` without being signed in does not error
- [ ] Visiting `/profile` while signed out redirects to `/login`
- [ ] Signed-in users visiting `/login` or `/register` are redirected to `/profile`
- [ ] `GET /login` still renders for signed-out visitors
- [ ] App starts with no errors and `/`, `/register`, `/terms` still work

## Notes for later steps

- Step 4 (profile) consumes `session["user_id"]` and `@login_required`
- Optional Step 4 hardening: `@app.before_request` loads the user into `g.user` and `session.clear()`s if that id no longer exists (cookie can outlive a reseeded `expense_tracker.db`)
- `next` query param to return to the page that required login — out of scope here
- Production: logout should be POST + CSRF; `SESSION_COOKIE_SAMESITE="Lax"` (Flask already sets `HttpOnly`)
- Unknown-email vs wrong-password timing is a minor enumeration signal — out of scope
- A "registered successfully" flash can be added here or in Step 4
- Landing page CTAs still show when signed in — out of scope
