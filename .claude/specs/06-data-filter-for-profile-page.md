# Spec: Data Filter for Profile Page

> **Status:** implemented on `feature/data-filter-for-profile-page` — see `.claude/plans/06-data-filter-for-profile-page.md`

## Overview

Step 5 gave `/profile` a full spending snapshot — totals, category breakdown, and recent transactions — but it always shows *everything* the user has ever spent. The product promise in `CLAUDE.md` is to "view spending by category and date range", and that is the missing half of the dashboard. This step adds a filter bar on the profile page so a signed-in user can narrow the snapshot to one category and/or a date range. Filters travel as GET query params, flow through the existing `get_summary_stats()` / `get_category_breakdown()` / `get_recent_transactions()` helpers (still the single source of truth), and apply equally to the page and the `/api/profile/`* JSON endpoints so those numbers can never diverge. Expense CRUD (Steps 7–9) comes next; this step makes the data we already have actually explorable.

## Depends on

- Step 1 — Database Setup (complete): `expenses` table with `user_id`, `amount`, `category`, `date`, `description`; `get_db()`, `CATEGORIES` in `database/db.py`
- Step 3 — Login and Logout (complete): `session["user_id"]`, `@login_required`, `g.user` loader
- Step 4 — Profile Page (complete): `/profile` dashboard, `.profile-*` layout, empty state
- Step 5 — Backend Routes for Profile Page (complete): `get_summary_stats()`, `get_category_breakdown()`, `get_recent_transactions()`, and the `/api/profile/stats`, `/api/profile/breakdown`, `/api/profile/history` endpoints that call them



## Routes

No new routes. Existing routes learn to read filter query params:

- `GET /profile` — accept optional `category`, `date_from`, `date_to` query params; pass them into the three helpers — logged-in
- `GET /profile/history` — same optional params, applied to the full history list — logged-in
- `GET /api/profile/stats` — same optional params — logged-in
- `GET /api/profile/breakdown` — same optional params — logged-in
- `GET /api/profile/history` — same optional params (in addition to the existing `limit`) — logged-in

`/`, `/register`, `/login`, `/logout`, `/terms`, `/profile/edit`, `/profile/password`, `/profile/delete` do not change behaviour. `/expenses/*` placeholders stay stubs.

## Database changes

No database changes. Verified against `database/db.py`:

- `expenses.date` is stored as ISO `YYYY-MM-DD` text (seed writes `date.isoformat()`), so string comparison in SQL (`date >= ?`, `date <= ?`) is correct — no date functions needed
- `expenses.category` is free-form `TEXT`, but the app only writes values from `CATEGORIES`; the filter dropdown must use `CATEGORIES` from `database/db.py`
- Every filter query still scopes with `WHERE user_id = ?` first — a filter must never widen visibility beyond the signed-in user



## Templates

- **Create:** `templates/partials/filter_bar.html` — include that does **not** extend `base.html`; a GET form with a category `<select>` (options from `CATEGORIES` plus an "All categories" empty value), `date_from` and `date_to` `<input type="date">` fields, a submit button, and a "Clear filters" link back to the unfiltered page. Field names must match the query params exactly: `category`, `date_from`, `date_to`. The form's `action` is passed in (or built with `url_for`) so the same partial works on `/profile` and `/profile/history`
- **Modify:** `templates/profile.html` — include the filter bar above the stats block; show a short "Filtered by …" line when any filter is active (category name and/or the date range as entered); when filters are active but match nothing, render a "No expenses match these filters" state that is **distinct** from the no-expenses-yet empty state, with a clear-filters link
- **Modify:** `templates/profile_history.html` — include the same filter bar; when filters are active and nothing matches, show the "no match" message (not "No transactions yet")



## Files to change

- `app.py` — extend the three helpers with optional filter arguments; parse and validate query params once (a small shared helper); thread filters through `/profile`, `/profile/history`, and the three `/api/profile/*` endpoints
- `templates/profile.html` — filter bar include, active-filter summary, no-match state
- `templates/profile_history.html` — filter bar include, active-filter summary, no-match state
- `static/css/style.css` — `.filter-*` styles only (see Rules)



## Files to create

- `templates/partials/filter_bar.html`



## New dependencies

No new dependencies.

## Rules for implementation



### Data and queries

- No SQLAlchemy or ORMs
- Parameterised queries only — never string-format SQL; build `WHERE` clauses with `?` placeholders and a params list
- Use `get_db()` from `database/db.py`; close the connection in `try/finally`
- Never `SELECT` or render `password_hash`
- The three helpers remain the single source of truth: `/profile` and every `/api/profile/*` endpoint must still call them, so filtered page numbers and JSON numbers cannot diverge
- Helper signatures gain optional filters with defaults that preserve current behaviour. Keep them keyword-friendly, e.g. `get_summary_stats(user_id, category=None, date_from=None, date_to=None)`, and apply the **same** filter clause shape in all three helpers
- Always keep `WHERE user_id = ?` as the first condition; append `AND category = ?`, `AND date >= ?`, `AND date <= ?` only when that filter is present
- `date_from` / `date_to` are inclusive on both ends (`>=` / `<=`) and compare as ISO `YYYY-MM-DD` strings
- When a category filter is active, the category breakdown must not silently "un-group" into other categories — the breakdown shows only the filtered rows. Bar percentages are still relative to the largest category **in the filtered result**
- Summary totals, expense count, breakdown, and recent/history rows must all honour the same filters — never filter some panels and not others
- Do not invent a second query path for JSON vs HTML



### Filter param parsing and validation

- Parse once and share: a small helper (e.g. `parse_expense_filters(request.args)`) used by every route that accepts filters
- `category` — empty/missing means "all"; a non-empty value that is not in `CATEGORIES` is **ignored** (treat as all) or rejected with a friendly error rendered on the page — do not pass unknown values into SQL as if they were valid
- `date_from` / `date_to` — accept only `YYYY-MM-DD`; empty/missing means unbounded on that side; a malformed date is ignored (or rejected with a friendly error) — never pass junk into SQL and never 500
- If both dates are present and `date_from > date_to`, show a friendly error on the page (same `{{ error }}` pattern as auth forms) and render the unfiltered snapshot — do not swap them silently
- Filters must be reflected back into the form controls after submit (`selected` / `value`) so the user can see and adjust what is active
- "Clear filters" links to the bare route with no query string



### Session and access

- Every filtered route stays behind `@login_required` — no public path to filtered data
- Filters never escape the signed-in user's rows: `user_id` comes from `g.user["id"]` only, never from the query string



### UI and CSS

- Use CSS variables — never hardcode hex values. The diff to `static/css/style.css` must add **no** new `#rrggbb` / `#rgb` literals
- Filter bar reuses the existing `.profile-*` card look; new classes are `.filter-*` only. Do not restyle the landing `dash-*` mockup or the auth form classes
- Category options come from `CATEGORIES` imported from `database/db.py` (pass them into the template, or use the existing pattern of exposing them the same way seed data does) — do not hardcode the seven category strings in the template
- Money format stays `"%.2f"|format(x)` → `₹1234.50` with `tabular-nums`
- Responsive: filter bar stacks or wraps cleanly at ≤600px, no horizontal scroll
- One stylesheet only: append to `static/css/style.css`. No new CSS files. Vanilla JS only if genuinely needed (`static/js/main.js`); a pure GET form needs **no** JS
- All templates extend `base.html` — except the filter-bar partial, which is an include like `partials/history_section.html`
- Distinguish three states clearly: (1) no expenses at all (existing empty state), (2) filters active with zero matches (new no-match state + clear link), (3) filters active with matches (show data + active-filter summary)



### General

- Passwords hashed with werkzeug (unchanged — this step never touches passwords)
- No CSRF protection — acceptable for this learning project (filters are read-only GETs anyway)
- Do not log or print emails or passwords



## Definition of done

Verified by running the app (`py app.py`) with the seeded demo user (`demo@spendly.com` / `demo123`) and its 8 sample expenses.

- [x] Signed-out visit to `/profile` still redirects to `/login`; no filter UI leaks on public pages
- [x] `/profile` shows the filter bar with a category dropdown listing All + the 7 `CATEGORIES` values, and date-from / date-to inputs
- [x] With no filters, `/profile` shows the unfiltered snapshot unchanged: 8 expenses, total **₹248.24**, breakdown Bills ₹60.00 … Other ₹4.99 (same as Step 4)
- [x] Selecting category `Food` and submitting shows only Food: 2 expenses, total **₹31.25**, breakdown bars only for Food, recent transactions only Food rows
- [x] Setting a date range covering only the first sample expense (the Food ₹12.50 row) shows 1 expense and that total alone
- [x] Combining category + date range applies both (AND logic) — e.g. Food in a range that includes only the ₹12.50 lunch shows exactly that one row
- [x] Total spend, expense count, category breakdown, and recent transactions all reflect the same filter — no panel shows unfiltered data while another is filtered
- [x] The active filter summary names what is applied (category name and/or the dates as entered) and the form controls still show the active values after submit
- [x] "Clear filters" returns to the unfiltered snapshot and empties the form controls
- [x] `/profile/history` accepts the same params and its list matches the filtered recent-transactions logic
- [x] `GET /api/profile/stats?category=Food` returns the same Food numbers the page shows (2 / 31.25); same check for `/api/profile/breakdown` and `/api/profile/history`
- [x] A category outside `CATEGORIES`, or a malformed date, does not 500 — the page renders with a friendly error or the invalid value ignored, per the chosen validation rule
- [x] `date_from` after `date_to` shows a friendly error and does not return a misleading empty/wrong set
- [x] Filters that match zero rows show the no-match state with a clear-filters link — **not** the "No expenses yet" copy and not `₹0.00` bars
- [x] A second signed-in user's filtered numbers never include another user's rows
- [x] Filter bar is usable at ≤600px (no horizontal scroll)
- [x] `git diff main -- static/css/style.css` adds no hex colour values (`#[0-9a-fA-F]{3,6}`)
- [x] App starts with no errors and `/`, `/register`, `/login`, `/terms`, `/logout`, `/profile/edit`, `/profile/password` still work