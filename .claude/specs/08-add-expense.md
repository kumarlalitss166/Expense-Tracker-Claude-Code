# Spec: Add Expense

> **Status:** implemented on `feature/add-expense` — see `.claude/plans/08-add-expense.md`

## Overview

Replace the `/expenses/add` stub with a signed-in **coming-soon** page for logging expenses — the same treatment Analytics already has. Right now the route returns a bare `"Add expense — coming in Step 7"` string, which is a dead end in the UI. This step gives it a real, navigable page with the project's `coming-soon-*` card so users can find the feature from the navbar and sidebar and understand it is on the roadmap.

This is deliberately **not** the create form yet. No expense is written, no fields are collected, and no schema changes. The actual add-expense form lands in a later step; this one only ships the placeholder surface and its navigation.

## Depends on

- Step 5 — Backend routes for profile page (complete): signed-in area and `@login_required` convention
- Analytics coming-soon (`/analytics`, `templates/analytics.html`): supplies the `coming-soon-*` card markup and CSS this page reuses

## Routes

- `GET /expenses/add` — render the coming-soon page — **logged-in** (`@login_required`). Replace the existing stub at `app.py:737`. Signed-out hit redirects to `/login`, same as `/analytics`.

No other routes change. `/expenses/<int:id>/edit` and `/expenses/<int:id>/delete` remain plain-string stubs for later steps.

No POST handler in this step.

## Database changes

No database changes.

## Templates

- **Create:** `templates/expense_add.html`
  - Extends `base.html` (same shell as `analytics.html`)
  - `{% block body_class %}add-expense-body{% endblock %}`
  - Reuses the exact `coming-soon-*` structure from `analytics.html`: blobs, card, corner accents, icon wrap + glow, badge, title, copy, progress dots + foot, line
  - Copy for this page:
    - Badge: `"Coming Soon"` (same string as Analytics)
    - Title: `"Add Expense"`
    - Body: `"We're building a simple way to log every rupee you spend — amount, category, date, and a note — so your dashboard stays up to date."`
    - Foot: `"We're crafting something special"` (same string as Analytics)
  - Icon: a rupee / plus-in-circle style SVG in the same `stroke-linecap="round"` style as the Analytics clock icon (keep the 24×24 viewBox)
  - `<h1>` id `add-expense-title`, section `aria-labelledby` pointing at it
- **Modify:** `templates/base.html`
  - In the signed-in `nav-links` block (next to Profile / Analytics), add:
    `<a href="{{ url_for('add_expense') }}" class="{% if request.endpoint == 'add_expense' %}is-active{% endif %}">Add expense</a>`
- **Modify:** `templates/partials/app_sidebar.html`
  - Add a `side-nav` item after "History": label `"Add expense"`, `href="{{ url_for('add_expense') }}"`, active when `request.endpoint == 'add_expense'`. Same `side-link` markup and inline SVG icon style as the existing rows

## Files to change

- `app.py` — replace the `add_expense()` stub with `@login_required` + `render_template("expense_add.html")`
- `templates/base.html` — signed-in navbar entry
- `templates/partials/app_sidebar.html` — sidebar entry
- `static/css/style.css` — in the "Analytics — coming soon" section, add `.add-expense-body` to the page-chrome selectors that currently key on `.analytics-body` (comma-separated, e.g. `.analytics-body, .add-expense-body { ... }`). Reuse every `.coming-soon-*` class as-is; do not duplicate them

## Files to create

- `templates/expense_add.html`
- `tests/test_08-add-expense.py`

## New dependencies

No new dependencies.

## Rules for implementation

- No SQLAlchemy or ORMs
- No database reads or writes in this step — the route is a pure render
- Use CSS variables where the existing `coming-soon-*` rules already do; do not hardcode new hex values
- `expense_add.html` extends `base.html`, **not** `dashboard.html` (matches `analytics.html`)
- `@login_required` on the route. Signed-out `GET /expenses/add` → `302` to `/login`
- Reuse the existing `coming-soon-*` CSS classes. Do not invent a parallel card system
- Keep the badge and foot copy identical to Analytics so the two placeholders feel like one family; only the title, body, icon, and `body_class` differ
- Do **not** add form fields, POST handling, or any `INSERT`
- Leave `/expenses/<int:id>/edit` and `/expenses/<int:id>/delete` stubs untouched
- Do not change `/analytics`, `templates/analytics.html`, or the Step 5 profile helpers/endpoints

## Definition of done

- [x] Signed-out `GET /expenses/add` redirects to `/login` (`302`)
- [x] Signed-in `GET /expenses/add` returns `200` and renders the coming-soon card with title `"Add Expense"`
- [x] The page shows the `"Coming Soon"` badge, the body copy, and the pulsing dots row
- [x] The page body uses `add-expense-body` and the card uses the shared `coming-soon-*` classes (no duplicated card CSS)
- [x] The signed-in marketing navbar shows an "Add expense" link that is `is-active` on this page
- [x] The app sidebar shows an "Add expense" link that is `is-active` on this page
- [x] `POST /expenses/add` still returns `405` (no POST handler added)
- [x] `/expenses/<id>/edit` and `/expenses/<id>/delete` still return their stub strings
- [x] `/analytics` still renders unchanged
- [x] `pytest tests/test_08-add-expense.py` passes, and the rest of the suite is still green
