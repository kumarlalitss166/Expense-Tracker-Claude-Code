---
name: project-forgot-password-accepted-risk
description: Step 7 forgot-password intentionally has no OTP/email/token — accepted by user and spec; do not report as a surprise finding
metadata:
  type: project
---

The `/forgot-password` flow (spec `.claude/specs/07-forgot-password.md`, commit `567b8a2`, 2026-10-04) intentionally has **no OTP, no email verification, and no reset tokens**. Anyone who knows an account's email can set a new password for it. This is documented in a `SECURITY (learning project)` comment above the route in `app.py` and in a visible `.form-hint` on `templates/forgot_password.html`. The explicit `"No account found with that email address."` message (and the 400-vs-302 status split) is also deliberate — the spec says not to swap it for a generic string.

**Why:** the user and spec explicitly accept this for the campus-x learning project; real apps email a single-use token. Re-reporting it as a Critical/High finding every review wastes attention.

**How to apply:** list it under "Accepted risk notes", not "Findings". Only raise a finding if something is *worse* than intended (e.g. mass assignment beyond `password_hash`, auto-login after reset, open redirect). Compounding issues like "existing sessions survive the reset" and "no rate limiting on the public mutation" are fair game as Low findings — see [[project-security-gaps]].
