# Spec: Backend Routes for Profile Page

> **Status:** implemented on `feature/backend-routes-for-profile-page` — see `.claude/plans/05-backend-routes-for-profile-page.md`

## Overview

Step 4 turned `/profile` into a read-only dashboard: identity, total spend, expense count, and a per-category breakdown. It shows who the user is but gives no way to correct it. This step adds the backend routes that make the profile page actionable — edit name and email, change the password, and delete the account. It closes out the account-management side of Spendly so that Steps 7–9 can focus entirely on expense CRUD without revisiting auth.

## Depends on

- Step 1 — Database Setup (complete): `users` table with `id`, `name`, `email`, `password_hash`, `created_at`; `get_db()`
- Step 2 — Registration (complete): `generate_password_hash` / `check_password_hash` conventions, email validation rules
- Step 3 — Login and Logout (complete): `session["user_id"]`, `@login_required`, `app.secret_key`, `load_user()` in `@app.before_request`
- Step 4 — Profile Page (complete): `g.user` populated on every request, `/profile` dashboard rendering

## Routes

- `GET /profile/edit` — render the name/email edit form — logged-in
- `POST /profile/edit` — validate and persist name/email changes, redirect to `/profile` — logged-in
- `GET /profile/password` — render the change-password form — logged-in
- `POST /profile/password` — verify current password, set new hash, redirect to `/profile` — logged-in
- `POST /profile/delete` — delete the account and its expenses, clear session, redirect to `/` — logged-in

`/`, `/register`, `/login`, `/logout`, `/terms`, `/profile` do not change behaviour. `/expenses/*` placeholders stay stubs.

## Database changes

No new tables or columns. Two existing behaviours change at the data layer:

1. `POST /profile/edit` runs `UPDATE users SET name = ?, email = ? WHERE id = ?`. The `email` column is already `UNIQUE` — a collision must surface as a friendly error, not a traceback.
2. `POST /profile/delete` removes rows from both tables. `expenses.user_id` is a foreign key **without** `ON DELETE CASCADE`, so delete the user's `expenses` rows first, then the `users` row.

## Templates

- **Create:** `templates/profile_edit.html` — extends `base.html`; form with `name` and `email` fields pre-filled from `g.user`, renders `{{ error }}`
- **Create:** `templates/profile_password.html` — extends `base.html`; form with `current_password`, `new_password`, `confirm_password`, renders `{{ error }}`
- **Modify:** `templates/profile.html` — add an account-management block with a link to `/profile/edit`, a link to `/profile/password`, and a delete-account button that POSTs to `/profile/delete` from a small confirm form. Keep the existing identity, stats, breakdown, and empty state untouched.

## Files to change

- `app.py` — add the five routes, reusing `@login_required`, `g.user`, and `get_db()`
- `templates/profile.html` — add the account-management block

## Files to create

- `templates/profile_edit.html`
- `templates/profile_password.html`

## New dependencies

No new dependencies.

## Rules for implementation

- No SQLAlchemy or ORMs
- Parameterised queries only
- Passwords hashed with werkzeug — `generate_password_hash` on write, `check_password_hash` on verify
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- Every new route is behind `@login_required`; there is no public path to account mutation
- Email validation on `/profile/edit` reuses the exact rules from `/register` (single `@`, non-empty local part, dot in domain, no leading/trailing/double dot)
- Changing the email to the address the user already owns must succeed, not collide with itself. Only reject when the address belongs to a **different** user id
- `/profile/password` must verify `current_password` against the stored hash before writing anything
- `/profile/password` must require `new_password` to be at least 8 characters (same floor as registration) and must require `new_password == confirm_password`
- Never pre-fill or echo back any password field on a failed submit
- `/profile/delete` must delete `expenses` rows for that `user_id` before the `users` row, then `session.clear()` — no orphan expenses
- Do not use `DELETE FROM users WHERE id = ?` while rows in `expenses` still reference it
- All error messages are plain strings rendered in the template (`{{ error }}`) — consistent with `/register` and `/login`, no flash framework
- Redirect to `/profile` after a successful edit or password change; redirect to `/` after account deletion
- Keep the existing CSS variable tokens; new form styles reuse `.form-*` patterns already in `static/css/style.css` where possible

## Definition of done

- [x] Signed in as `demo@spendly.com`, visiting `/profile/edit` shows the current name and email pre-filled in the form
- [x] Changing the name and saving redirects to `/profile`, where the new name appears immediately
- [x] Changing the email to a fresh address works; signing out and signing in with the new address succeeds
- [x] Changing the email to one already used by another account shows a friendly error and does not modify the row
- [x] Leaving name or email blank shows the same style of validation error as `/register`
- [x] Visiting `/profile/password`, entering the wrong current password shows an error and leaves the stored hash unchanged
- [x] Entering the correct current password plus a matching new password of 8+ characters succeeds; signing out and signing in with the new password works
- [x] New password under 8 characters, or mismatched confirmation, shows an error and does not update the hash
- [x] A logged-out request to any of the five new routes redirects to `/login`
- [x] The delete-account form on `/profile` submits a POST (not a GET link) and asks for confirmation before submitting
- [x] Deleting the account removes the user and all their expenses from `expense_tracker.db`; a second login with those credentials fails
- [x] After deletion the browser lands on the landing page with the signed-out nav state
- [x] No page throws a 500: form resubmission, stale session mid-edit, and duplicate email all return a rendered page with `{{ error }}`
