# Spec: Forgot Password

> **Status:** implemented on `main` (`567b8a2`) and `feature/forgot-password` — see `.claude/plans/07-forgot-password.md`

## Overview

Give signed-out users a way back into their account from the sign-in page. A **Forgot password?** link opens a reset form that takes the account email plus a new password (typed twice). On submit the app updates that user's `password_hash` immediately and sends them to `/login?reset=1`, where a success banner tells them to sign in with the new password.

This step deliberately uses **no OTP, no emailed link, and no confirmation token** — accepted for this campus-x learning project and called out in the UI (`form-hint`) and above the route (`SECURITY` comment). Real products email a single-use token. The flow reuses existing auth conventions: Werkzeug hashing, `is_valid_email()`, and `render_template(..., error=...), 400` on validation failures. The app has no `flash()`; success uses the same `success=` template-kwarg pattern as `error=`.

## Depends on

- Step 1 — Database Setup (complete): `users` table with `password_hash`, `get_db()`
- Step 2 — Registration (complete): `is_valid_email()`, password minimum of 8 characters
- Step 3 — Login and Logout (complete): `/login` accepts the new password; success banner target is `GET /login`

## Routes

- `GET /forgot-password` — render `forgot_password.html` — public. If `"user_id" in session`, redirect to `/profile`
- `POST /forgot-password` — validate, look up user by email, `UPDATE` `password_hash`, redirect to `/login?reset=1` — public
- `GET /login` — **modified**: when `request.args.get("reset") == "1"`, pass `success="Your password has been reset. Sign in with your new password."` into `login.html` — public

No other routes change. `/profile/password` (signed-in change-password) stays as-is.

## Database changes

No database changes. Reset only writes `users.password_hash`. Do **not** add tokens, reset timestamps, or OTP tables.

## Templates

- **Create:** `templates/forgot_password.html`
  - Extends `base.html` (public shell)
  - Same `auth-section` / `auth-container` / `auth-header` / `auth-card` structure as `login.html`
  - Title `"Reset your password"` / subtitle `"Choose a new password for your Spendly account"`
  - Form `method="POST" action="/forgot-password"` (hardcoded path, matching `login.html` / `register.html`)
  - Fields (ids use hyphens, `name`s use underscores — same as `profile_password.html`):
    - `email` — `type="email"`, placeholder `nitish@example.com`, `required autofocus`
    - `new_password` — id `new-password`, placeholder `Min. 8 characters`, `required`
    - `confirm_password` — id `confirm-password`, placeholder `Repeat the new password`, `required`
  - Submit `.btn-submit` label `"Reset password"`
  - Under the form, `.form-hint`: `"Learning project: no email check — anyone who knows your email can reset this password."`
  - Footer `.auth-switch`: `"Remembered it?"` + link to `url_for('login')` labeled `"Sign in"`
- **Modify:** `templates/login.html`
  - Inside `.auth-card`, before the `{% if error %}` block: `{% if success %}<div class="auth-success">{{ success }}</div>{% endif %}`
  - Under the password input, inside that `.form-group`: `<p class="auth-forgot"><a href="{{ url_for('forgot_password') }}">Forgot password?</a></p>`

## Files to change

- `app.py` — `forgot_password()` after `login()`; `login()` GET reads `reset=1` and passes `success=`
- `templates/login.html` — success banner + forgot-password link
- `static/css/style.css` — `.auth-success`, `.form-hint`, `.auth-forgot` (+ link hover) in the "Auth pages" section, after `.auth-error`

## Files to create

- `templates/forgot_password.html`
- `tests/test_07-forgot-password.py`

## New dependencies

No new dependencies.

## Rules for implementation

- No SQLAlchemy or ORMs
- Parameterised queries only — never string-format SQL
- Passwords hashed with werkzeug (`generate_password_hash`)
- Use CSS variables for tokens (`--accent`, `--accent-light`, `--ink-faint`, `--radius-sm`). The success banner border uses a literal tint `#b7d3c2`, matching the existing `.auth-error` border (`#f5c6c2`) pattern in this file
- `forgot_password.html` extends `base.html` (public pages only)
- Use `get_db()` from `database/db.py`; close the connection in `try/finally`
- Route is **public** — no `@login_required`. Signed-in `GET /forgot-password` → `redirect(url_for("profile"))`
- Strip and lowercase `email`. Never strip passwords
- Validation order and exact error strings (HTTP `400`, re-render `forgot_password.html` with `error=`, never redirect):
  1. Any of `email` / `new_password` / `confirm_password` empty → `"Please fill in all fields."`
  2. `is_valid_email(email)` fails → `"Please enter a valid email address."`
  3. `len(new_password) < 8` → `"Password must be at least 8 characters."`
  4. `new_password != confirm_password` → `"New passwords do not match."`
  5. No `users` row for that email → `"No account found with that email address."`
- Unknown email uses the **explicit** message above (learning project). Do not swap it for a generic string
- Write only `password_hash` (`UPDATE users SET password_hash = ? WHERE id = ?`) — never plaintext, never `name` / `email`
- Success: `redirect(url_for("login", reset=1))` → `302` Location path `/login`, query `reset=1`. **Do not** set session / auto-login
- `login()` GET success string (when `reset == "1"`): `"Your password has been reset. Sign in with your new password."` (`reset` values other than `"1"` → no banner)
- Keep the `SECURITY (learning project): …` comment above the `@app.route("/forgot-password")` decorator
- Keep the visible `form-hint` security line on the page

## Definition of done

- [x] Sign-in page shows a **Forgot password?** link that opens `/forgot-password`
- [x] `GET /forgot-password` renders a form with `email`, `new_password`, and `confirm_password` fields and a link back to sign-in
- [x] `GET /forgot-password` while signed in redirects to `/profile`
- [x] Submitting the form with a valid email and matching new passwords updates that account and returns `302` to `/login` (with `reset=1` in the query string)
- [x] After a successful reset the user can sign in with the **new** password
- [x] After a successful reset the **old** password is rejected (`400`, `"Invalid email or password."`)
- [x] After a successful reset the user is **not** signed in — `/profile` still redirects to `/login`
- [x] `/login?reset=1` shows the success banner text
- [x] Empty fields return `400` and `"Please fill in all fields."`
- [x] A malformed email returns `400` and `"Please enter a valid email address."`
- [x] A password shorter than 8 characters returns `400` and `"Password must be at least 8 characters."`
- [x] Mismatched new/confirm passwords return `400` and `"New passwords do not match."`
- [x] An email with no account returns `400` and `"No account found with that email address."`
- [x] Email matching is case-insensitive (stored lowercased emails still resolve)
- [x] The reset page shows the learning-project security hint
- [x] `pytest tests/test_07-forgot-password.py` passes; full suite still passes
