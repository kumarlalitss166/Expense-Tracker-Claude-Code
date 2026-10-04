---
name: reference-auth-session-map
description: Where Spendly auth, session handling, and password hashing live — quick map for security reviews
metadata:
  type: reference
---

Security-relevant locations in Spendly (verify before citing line numbers — they drift):

- `app.py` — all routes. Auth helpers at top: `login_required`, `@app.before_request load_user()` (attaches `g.user`, clears stale sessions). `is_valid_email()` shared by register/profile-edit. Auth routes: `/register`, `/login`, `/logout`, `/forgot-password`. Signed-in password change at `/profile/password` (`change_password`), account deletion at `/profile/delete`.
- `database/db.py` — SQLite layer: `get_db()`, `init_db()`, `seed_db()`. DB file `expense_tracker.db`. `PRAGMA foreign_keys = ON`.
- Passwords: Werkzeug `generate_password_hash` / `check_password_hash`; minimum length 8 enforced in register, change-password, and forgot-password. Passwords are never stripped; emails are stripped + lowercased.
- Tests: `tests/test_<step>-<slug>.py`, one file per curriculum step. Root `conftest.py` repoints `database.db.DB_PATH` at a temp file before `app` is imported.

Standing gaps that interact with auth are in [[project-security-gaps]]; the Step 7 no-OTP decision is in [[project-forgot-password-accepted-risk]].
