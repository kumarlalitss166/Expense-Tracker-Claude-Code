# Spec: Profile Page

> **Status:** implemented on `feature/profile-page` — see `.claude/plans/04-profile-page.md`

## Overview

Turn the `/profile` stub into a real signed-in dashboard. Steps 1–3 already give us a `users` table, registration, and a session-backed `@login_required` on `/profile`, but the route still returns plain text. This step renders a profile page showing who is signed in (name, email, member-since) and a spending snapshot for that user only: total spend, expense count, and a per-category breakdown. It also adds a `@app.before_request` user loader so the session can never point at a user row that no longer exists (for example after the DB is deleted and reseeded). This is the first logged-in surface in Spendly and the visual base the later expense pages will reuse.

## Depends on

- Step 1 — Database Setup (complete): `users`, `expenses`, `get_db()`
- Step 2 — Registration (complete): accounts can be created
- Step 3 — Login and Logout (complete): `session["user_id"]`, `@login_required` already on `/profile`, `inject_auth` context processor



## Routes

No new routes.

- `GET /profile` — existing route behind `@login_required`; replace the stub string with `render_template("profile.html", ...)` — logged-in

`/expenses/*` placeholders stay stubs. `/`, `/register`, `/login`, `/logout`, `/terms` do not change behaviour.

## Database changes

No database changes. Verified against `database/db.py`:

- `users(id, name, email, password_hash, created_at)` — `created_at` defaults to `datetime('now')` (UTC) and is nullable
- `expenses(id, user_id, amount, category, date, description, created_at)` with `FOREIGN KEY (user_id) REFERENCES users(id)` and `PRAGMA foreign_keys = ON` in `get_db()`

Note: there is **no** `ON DELETE CASCADE`, so a user with expenses cannot be deleted. See Definition of done.

## Templates

- **Create:**
  - `templates/profile.html` — extends `base.html`, `{% block title %}` "Profile · Spendly", `{% block content %}`
- **Modify:**
  - `templates/base.html` — when `is_logged_in`, add a "Profile" link (`url_for('profile')`) **before** the existing Sign out link. Sign out **must keep** `class="nav-cta"` so it survives the ≤600px rule in `static/css/style.css` (`.nav-links a:not(.nav-cta) { display: none; }`). The plain Profile link will hide on mobile — that is intended; login already lands on `/profile`, and Sign out stays reachable.

No other templates change.

## Files to change

- `app.py` — `before_request` user loader; `GET /profile` handler body
- `templates/base.html` — signed-in nav gains a Profile link
- `static/css/style.css` — new `.profile-*` styles only (see Rules)

Imports `app.py` will need:

- `g` from `flask` (for the loader) — `redirect`, `render_template`, `request`, `session`, `url_for` are already imported



## Files to create

- `templates/profile.html`



## New dependencies

No new dependencies.

## Rules for implementation



### Data and queries

- No SQLAlchemy or ORMs
- Parameterised queries only — never string-format SQL
- Use `get_db()` from `database/db.py`; close the connection in `try/finally`
- Never `SELECT` or render `password_hash`
- Snapshot SQL for the signed-in user only (`WHERE user_id = ?`):
  - `COUNT(*)` and `COALESCE(SUM(amount), 0)` — `SUM` is `NULL` on zero rows, so `COALESCE` is required
  - Category breakdown: `SELECT category, COUNT(*) AS n, COALESCE(SUM(amount), 0) AS total FROM expenses WHERE user_id = ? GROUP BY category ORDER BY total DESC` (largest category first)
- Do not load or list individual expense rows in this step — that is the expenses list (later step)



### Session hardening (`before_request`)

- Import `g` from `flask`
- Always start with `g.user = None` so handlers and templates can rely on the attribute existing
- Skip the DB hit when `request.endpoint == "static"` or `"user_id"` is not in `session`
- When signed in, load `SELECT id, name, email, created_at FROM users WHERE id = ?` — the same row `/profile` renders, so the handler must **not** query the user again
- If no row comes back, `session.clear()` and leave `g.user` as `None` (the existing `login_required` will then redirect)
- Leave `login_required` and `inject_auth` reading `session` — do **not** rewrite them; the loader clears a stale session before either runs



### Profile page content and empty state

- Render from `g.user`: `name`, `email`, and member-since
- "Member since" shows **month + year only** (e.g. "Sep 2026") — SQLite's `datetime('now')` is UTC while `seed_one_user.py` writes local time, so day-level display can be off by one near midnight IST. Parse with stdlib `datetime.strptime` / `strftime`; handle `created_at IS NULL` gracefully (omit the line) — do not add a date library
- Money format: `"%.2f"|format(x)` → `₹1234.50`, with `font-variant-numeric: tabular-nums`. No thousands grouping (Jinja has no Indian grouping built in)
- If expense count is 0: render **only** the empty-state block (e.g. "No expenses yet") and hide the totals row and category breakdown entirely — never show `₹0.00` bars
- Do **not** link to `/expenses/add` as a working CTA — it is still a plain-text stub. Render a non-link "coming soon" chip, or a disabled-looking control with no `href`



### CSS and design

- Use CSS variables — never hardcode hex values. The diff to `static/css/style.css` must add **no** new `#rrggbb` / `#rgb` literals (the file already has some in the landing `dash-`* mockup; do not add more). New `:root` tokens only if genuinely needed
- Category bars: all bars use `var(--accent)`, width set by percentage of the largest category. Do **not** invent per-category colours
- Do not reuse `auth-card` (capped at `--auth-width: 440px`) or form classes (`form-group`, `btn-submit`) — this page has no form. Add `.profile-*` classes
- The landing page's `dash-*` block is the closest visual reference for a spending snapshot (stat cards + bar rows); reuse its *layout ideas*, not its markup or hex-coloured bar classes
- One stylesheet only: append to `static/css/style.css`. No new CSS files, no new JS, no new CDNs
- All templates extend `base.html`
- Responsive: usable at ≤600px (stack the stat cards, no horizontal scroll)



### General

- Passwords hashed with werkzeug (unchanged — this step never touches passwords)
- No CSRF protection — acceptable for this learning project
- Do not log or print emails or passwords



## Definition of done

Verified by running the app (`py app.py`).

- [x] Signed-out visit to `/profile` redirects to `/login` (unchanged from Step 3)
- [x] Signing in as `demo@spendly.com` / `demo123` lands on a real profile page (no "coming in Step 4" text)
- [x] Profile shows the user's name, email, and "Member since" month + year (e.g. "Sep 2026")
- [x] On a **freshly seeded DB**, the demo user sees 8 expenses and total **₹248.24**
- [x] Category breakdown on a fresh DB, sorted largest-first: Bills ₹60.00, Shopping ₹55.00, Transport ₹45.00, Food ₹31.25, Entertainment ₹30.00, Health ₹22.00, Other ₹4.99
- [x] Register a second user B, seed expenses for B (`/seed-expense` or equivalent), sign in as B: B sees only B's totals. Sign back in as demo: demo still sees only demo's numbers
- [x] Register a **fresh user with no expenses** and sign in: empty state only — no totals row, no category bars, no "₹0.00"
- [x] That same fresh user (no expenses) can be deleted: delete their `users` row in SQLite, refresh `/profile`, and they are redirected to `/login` (stale session cleared). *Do not try this with the demo user —* `PRAGMA foreign_keys = ON` *and no* `ON DELETE CASCADE` *means deleting a user who has expenses fails with* `FOREIGN KEY constraint failed`
- [x] After the stale-session clear above, nav shows "Sign in" / "Get started" again
- [x] When signed in, nav shows "Profile" and "Sign out"; "Sign out" still has `nav-cta` and is visible at ≤600px width
- [x] Profile page is usable at ≤600px (no horizontal scroll; stats stack)
- [x] `git diff main -- static/css/style.css` adds no hex colour values (`#[0-9a-fA-F]{3,6}`)
- [x] No page source or server log shows `password_hash`
- [x] App starts with no errors and `/`, `/register`, `/login`, `/terms`, `/logout` still work



## Notes for later steps

- Expense list / add / edit / delete (Steps 7–9) reuse `g.user` and the `.profile-*` card layout
- Optional later: a "registered successfully" flash on `/login` (needs `flash` + session — Step 3 left this out on purpose)
- Landing page CTAs still show when signed in — out of scope
- `next` query param (return to the page that required login) — out of scope
- Production: logout should be POST + CSRF; `SESSION_COOKIE_SAMESITE="Lax"` (Flask already sets `HttpOnly`)
- `created_at` is mixed UTC/local across writers; if that ever matters, normalise writes in `db.py` first
- `CLAUDE.md` references `docs/UI Design Templates/`, which holds landing mockups only — there is no profile mockup; this page is built from the landing `dash-*` snapshot style

