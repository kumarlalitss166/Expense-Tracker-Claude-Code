---
name: project-security-gaps
description: Standing project-wide security gaps in Spendly — CSRF missing everywhere, debug=True, no rate limiting, client-side sessions never invalidated
metadata:
  type: project
---

Project-wide security properties that predate any single feature and apply everywhere. Mention each ONCE per review as a known topic — not as a new per-route finding.

- **No CSRF protection anywhere** — no tokens, no Flask-WTF. Accepted for the campus-x learning project. Flag once per review as a future learning topic.
- **`debug=True` hardcoded** in `app.run(...)` at the bottom of `app.py` — production concern worth knowing about; mention once.
- **No rate limiting** on any auth endpoint (login, register, forgot-password). Login brute force is a standing pre-existing surface.
- **Sessions are client-side cookies holding `user_id` only** — no password/session version claim. Consequence: password changes and resets do NOT invalidate existing sessions; only `/logout` (per browser) ends one. Recurring pattern worth watching in any future auth feature.
- **`app.secret_key` falls back to `"dev-secret-change-me"`** when `SECRET_KEY` env var is unset — standing pre-existing note.

**Why:** these are durable, repo-level gaps the curriculum has consciously deferred; re-flagging them as fresh findings on every diff would drown the real feature review.

**How to apply:** when reviewing any feature diff, put these in "Accepted risk notes" or "Out of scope / not flagged" rather than "Findings", unless the new code makes one of them materially worse. See [[project-forgot-password-accepted-risk]] for the Step 7 accepted risk.
