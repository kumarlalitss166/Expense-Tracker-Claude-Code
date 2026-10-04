# MEMORY.md

- [Project-wide security gaps](project-security-gaps.md) — CSRF missing everywhere, debug=True, no rate limiting, cookie-only sessions
- [Forgot-password accepted risk](project-forgot-password-accepted-risk.md) — no OTP/token by design; do not re-litigate
- [Auth and session map](reference-auth-session-map.md) — where auth, sessions, and password hashing live in Spendly
