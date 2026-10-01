---
name: test-api-contracts
description: JSON shapes of Spendly /api/profile/stats|breakdown|history — documented only in app.py docstrings, not in any spec
metadata:
  type: project
---

Stable JSON contracts for the Step 5 profile endpoints (Steps 06+ reuse them without changing shape):

- `GET /api/profile/stats` -> `{"expense_count": <int>, "total_spend": <float>}`
- `GET /api/profile/breakdown` -> `{"breakdown": [{"category", "count", "total", "bar_pct"}, ...]}` ordered by total DESC; `bar_pct` is relative to the largest category in the (filtered) result, rounded to 1 decimal, 0 when empty.
- `GET /api/profile/history` -> `{"transactions": [{"id", "amount", "category", "date", "description"}, ...], "count": <int>}` newest first (`date DESC, id DESC`); `limit` query param, clamped 1..100, default 20.

**Why:** no `.claude/specs/` file documents these keys (the Step 5 spec covers account management only) — the only written contract is the helper docstrings in `app.py`. The 06 spec says the filtered routes keep the existing response shape.

**How to apply:** assert these keys when testing `/api/profile/*` (including filter behaviour). Filter query params on all filtered routes: `category`, `date_from`, `date_to` (plus `limit` on history). `profile_history` route renders up to 100 rows; `/profile` recent list is 5. See [[test-conventions]].
