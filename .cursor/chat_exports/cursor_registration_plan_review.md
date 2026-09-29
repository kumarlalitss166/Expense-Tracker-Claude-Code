# Registration plan review
_Exported on 9/29/2026 at 15:29:37 GMT+5:30 from Cursor (3.20.21)_

---

**User**

@Claude-Code-CLI/campus-x-Claude-CLI/expense-tracker/.claude/specs/02-registration.md cross check this plan

---

**Cursor**

I'll read the spec and the current project code to check it against reality.

The spec is accurate and safe to implement. Every assumption it makes about the code holds. It has a few gaps you should close first so Claude doesn't have to guess: how to detect duplicate emails, closing the database connection, and trimming the name.

## What checks out

| Spec claim | Reality |
|---|---|
| Step 1 is done: `users` table, `get_db()`, `init_db()` | True. `database/db.py` has all three, plus `seed_db()` |
| `users` has `id`, `name`, `email` (unique), `password_hash`, `created_at` | True. `created_at` defaults to `datetime('now')`, so that checklist item passes automatically |
| `register.html` posts to `/register` and shows `{{ error }}` | True. It extends `base.html`, and `.auth-error` is styled in `style.css` |
| `/register` currently handles GET only | True. It's a bare `render_template` in `app.py` |
| No new dependencies | True. Werkzeug is already installed and used in `db.py` |
| Only `app.py` changes | Correct |

The existing emails also fit the lowercase rule. The demo seed uses `demo@spendly.com`, and `seed_one_user.py` builds emails from lowercased names. So the "normalise to lowercase" rule won't clash with existing rows.

## Gaps to tighten before implementing

1. **Duplicate-email detection isn't specified.** The spec says what should happen, not how. Recommend: catch `sqlite3.IntegrityError` on the insert, because the `UNIQUE` constraint is the real guard. A `SELECT` first is optional for a friendlier message, but on its own it has a race window (two requests could both pass the check before either inserts). Importing `sqlite3` in `app.py` for the exception is fine; it doesn't break the "don't open connections by hand" rule.

2. **No rule about closing the connection.** `get_db()` returns a raw connection. Add a rule like "wrap DB work in `try/finally: conn.close()`, same pattern as `db.py`". Otherwise every error path leaks a connection.

3. **Whitespace-only input.** The checklist only says "empty name or email". Add: strip `name` and `email` before validating, so `"   "` is rejected. **Don't** strip the password.

4. **No server-side email format check.** `type="email"` only validates in the browser; a direct POST skips it. Add a minimal check (e.g. contains `@` and a `.` after it) and a matching checklist item.

5. **The form loses the user's input on error.** Because the spec prefers leaving the template unchanged, a failed submit clears name and email. Decide one way:
   - Keep it simple and accept losing the input, or
   - Allow a small template change: `value="{{ name or '' }}"` and `value="{{ email or '' }}"`, and pass those from the handler. Never pre-fill the password.

6. **Imports aren't listed.** `app.py` will need `request`, `redirect`, `url_for` from Flask, plus `generate_password_hash` and `sqlite3`. One line in "Files to change" saves Claude a guess.

7. **Optional: return a 400 status on validation errors.** Use `render_template(...), 400`. It's better practice and makes later pytest checks cleaner. This isn't required by the curriculum.

## Minor notes

- **Stray `---` on line 1.** It was copied from the `create-spec` template delimiters. Some tools read a leading `---` as the start of front matter, so delete it.
- **No "registered successfully" message on `/login`.** That's consistent with "no sessions here", since Flask's `flash()` needs a session and a `SECRET_KEY`. Just be aware of it. Step 3 can add flash messages.
- **The demo password `demo123` is only 7 characters.** That's fine, because the 8-character minimum is for registration only. But when you write the Step 3 (login) spec, make sure login does **not** enforce the minimum, or the demo user can't sign in.
- **The "refresh doesn't duplicate" checklist item** is already covered by redirecting after the POST, with the unique constraint as backup. Keep it; it's a good manual test.
- **No CSRF protection.** Acceptable for a learning project. It's worth knowing about for interviews.

## Repo state

- You're on `feature/registration-01`, because `feature/registration` already existed from an earlier run. That older branch is identical to `main`, so you can delete it with `git branch -d feature/registration`.
- The spec file is untracked. Commit it on this branch before implementing so the spec and code stay together.
- `CLAUDE.md` is out of date: it still calls `db.py` a "Stub for Step 1" and says password hashing isn't implemented. `create-spec` tells Claude to read `CLAUDE.md`, so updating those two lines stops future specs from being based on wrong information.

## Suggested additions

Add these to the rules section:

```markdown
- Strip `name` and `email`; lowercase `email`. Never strip `password`
- Reject whitespace-only name/email and emails without a basic `@` + domain shape
- Detect duplicate email by catching `sqlite3.IntegrityError` on INSERT (optionally pre-check with SELECT for a friendly message)
- Always close the connection in `try/finally`, matching `database/db.py`
- On validation failure, return `render_template("register.html", error=...), 400`
```

And to the definition of done:

```markdown
- [ ] Whitespace-only name or email shows an error and does not insert
- [ ] Registering `Demo@Spendly.com` (mixed case) is rejected as a duplicate of the seed user
```

I'm in Ask mode, so I haven't edited anything. Switch to Agent mode if you want me to apply these to the spec.

