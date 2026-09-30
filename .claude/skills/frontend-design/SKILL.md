---
name: spendly-frontend-design
description: Designs and builds UI for the Spendly expense tracker (Flask + Jinja2 + vanilla CSS/JS) using the repo's existing design tokens, classes, and spec rules. Use when asked to design, build, redesign, or style any Spendly page or component (profile, dashboard, expense forms, tables, empty states), or to improve its layout, CSS, or responsiveness.
disable-model-invocation: true
---

# Spendly Frontend Design

Build UI that looks like it belongs to the existing Spendly product: warm paper background, white cards, serif headings, dark-green accent. Consistency with `static/css/style.css` beats novelty.

## Hard constraints

- Stack: Flask, server-rendered Jinja2, vanilla CSS, vanilla JS. No React/Vue/Tailwind/Bootstrap, no icon libraries (no Lucide), no new CDNs (Google Fonts in `base.html` is the only one), no new pip/npm dependencies.
- Every template extends `base.html` and fills `{% block content %}`.
- **Colours come from CSS variables only.** Never write a hex value outside `:root`. New tokens may be added to `:root` only when genuinely needed.
- One stylesheet: append to `static/css/style.css`. Do not create new CSS files.
- No JavaScript unless the spec asks for it. Leave `static/js/main.js` alone otherwise.
- Do not add routes, change DB logic, or touch password handling as part of a styling task. Follow the active spec in `.claude/specs/`.

## Before designing (mandatory reads)

1. `CLAUDE.md` and the relevant `.claude/specs/NN-*.md` (its rules override this skill).
2. `static/css/style.css`: the `:root` tokens and the classes that already exist.
3. `templates/base.html`: navbar, footer, block names.
4. `templates/landing.html`: the `dash-*` dashboard mockup (`dash-card`, `dash-label`, `dash-amount`, `dash-bars`, `dash-bar-track`, `dash-txns`, `dash-legend`) is the closest visual reference for stats, category breakdowns, and recent lists.

Note: `CLAUDE.md` mentions `docs/UI Design Templates/`, which does not exist. Use `landing.html` instead.

## Design tokens (defined in `:root`)

| Purpose | Tokens |
|---|---|
| Text | `--ink`, `--ink-soft`, `--ink-muted`, `--ink-faint` |
| Surfaces | `--paper` (page), `--paper-warm`, `--paper-card` (cards) |
| Accent | `--accent` (dark green), `--accent-light`, `--accent-2` (amber), `--accent-2-light` |
| Status | `--danger`, `--danger-light` |
| Borders | `--border`, `--border-soft` |
| Type | `--font-display` (DM Serif Display), `--font-body` (DM Sans) |
| Layout | `--max-width` (1200px), `--auth-width` (440px) |
| Radius | `--radius-sm` (6px), `--radius-md` (12px), `--radius-lg` (20px) |

There are no shadow or spacing tokens. Use `rem`/px on a 4/8px grid and keep shadows very subtle, preferring a `var(--border)` border to a shadow.

## Existing classes to reuse first

- Buttons: `btn-primary`, `btn-ghost` (general), `btn-submit` (form submit).
- Forms/auth: `auth-section`, `auth-container`, `auth-header`, `auth-title`, `auth-subtitle`, `auth-card`, `auth-error`, `form-group`, `form-input`, `auth-switch`.
- Layout: `navbar`, `main-content`, `hero*`, `dash-*`.
- `auth-card` is limited to `--auth-width` (440px) and is for narrow forms. Do not stretch it into a dashboard-width container; create a prefixed class instead.

## Visual language

- Warm, calm, trustworthy. Serif (`--font-display`) for page and section titles, sans for everything else.
- Card-based: group related info in `--paper-card` surfaces with `--border` and `--radius-md`.
- One primary accent (`--accent`), amber for secondary emphasis, `--danger` only for errors or destructive actions. Everything else neutral.
- Generous whitespace, left-aligned content, clear hierarchy. Solid colours over gradients.
- A clearly labelled button beats an icon-only one. For small glyphs use text characters (like the brand `◈`) or a small inline SVG.

## Money and data display

- Amounts: rupee prefix, two decimals (`₹{{ "%.2f"|format(x) }}`), `font-variant-numeric: tabular-nums`, right-aligned in tables.
- Every list or stat block needs an empty state with friendly copy ("No expenses yet"). Never render `None`, NULL, or a bare `0` as if it were data.
- Category bars: fill with `var(--accent)` and set width by percentage. Per-category colours need `--cat-*` tokens added to `:root` first. Do not copy the `dash-bar-*` hex colours.
- Dates: format in the handler or template with the stdlib only (no date library). Handle missing values gracefully.
- Never render `password_hash` or any password material.

## Responsive rules

- Must work at 600px and below. Stack cards vertically, wrap flex rows, make wide tables horizontally scrollable.
- `style.css` hides plain nav links at 600px: `.nav-links a:not(.nav-cta) { display: none; }`. Any link users must reach on mobile (for example Sign out) must keep `class="nav-cta"`.

## Workflow

1. **UI plan** (2-5 bullets): sections, key UX decisions, and any assumptions stated up front. Ask a question only if the answer would change the output.
2. **Implement in place**: edit or create the Jinja template, append page-prefixed classes (`.profile-*`, `.expense-*`) to `style.css`. Use Jinja control flow with the variable names the route provides.
3. **Integration note** (1-3 lines): which route renders it and what variables the template expects.
4. **Verify**: run the app (`py app.py`) and check the checklist below.

## Verification checklist

- [ ] Template extends `base.html`; app starts with no errors; existing routes still render
- [ ] `git diff -- static/css/style.css` adds no hex values outside `:root`
- [ ] Looks right at desktop width and at 600px or narrower; navigation still usable
- [ ] Empty state shown when there is no data; no `None` or stray zeros
- [ ] Amounts show the rupee prefix and two decimals
- [ ] No new JS, dependencies, stylesheets, or routes beyond the spec

## Avoid

- Generic or dated styling (default browser look, sharp bordered boxes).
- Inconsistent spacing or random accent colours.
- Duplicating CSS that an existing class already provides.
- Unscoped class names that could leak into other pages.
- Stretching `auth-card` beyond forms.
