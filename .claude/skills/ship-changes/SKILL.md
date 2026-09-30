---
name: ship-changes
description: After a plan is implemented, refresh project docs to match the code, then stage, commit with one themed message, and push to the current remote branch. Use when asked to ship, commit, push, sync docs, or wrap up a finished step/plan.
disable-model-invocation: true
---

# Ship Changes

Close out an implemented plan: make the docs tell the truth about the code,
then land everything as **one themed commit** on the branch you are already
on and push it.

This is a workflow skill, not a coding skill. Do not write feature code here.
If the implementation is incomplete, stop and say so.

## When to run

- A plan in `.claude/plans/` has just been implemented and verified
- The user says "ship it", "commit and push", "update docs and push", or "wrap up this step"
- Working tree has the finished work for one step / one theme

Do **not** run this mid-implementation, or with unfinished/unverified changes.

---

## Step 1 — Confirm state

Run:

```bash
git status -sb
git branch --show-current
git log --oneline -5
```

Check:

1. You are on a real branch (not detached HEAD).
2. The changes look finished — no stub text like "coming in Step N", no
   commented-out experiments, no leftover debug prints.
3. The work is one coherent theme (e.g. "Step 4 profile page"). If the tree
   mixes two unrelated efforts, **stop and ask** whether to split into two
   branches first.

If the tree is empty, say "nothing to ship" and stop.

---

## Step 2 — Read the codebase (what actually landed)

Do not trust memory. Read what changed.

```bash
git diff --stat
git diff
git status -porcelain
```

Then read the surrounding truth-tellers so docs can be updated accurately:

| Read | Why |
|---|---|
| `CLAUDE.md` | Architecture table, "current state", step placeholders |
| `.claude/specs/<step>-*.md` | The step being shipped — Definition of done |
| `.claude/plans/<step>-*.md` | The plan that was implemented |
| The files in the diff | Ground truth for what the docs must now say |
| `app.py` route comments | Curriculum step markers ("coming in Step N") |

Note specifically:

- Routes that changed from stub → real
- New templates / CSS / DB helpers
- Any step markers still claiming work is undone
- Spec checklist items that are now true

---

## Step 3 — Update the docs

Docs must match the code after this commit. Update only what the diff
invalidates — do not rewrite docs for unrelated steps.

### `CLAUDE.md`

- Refresh the **Project** "Current state" line if it is stale
  (e.g. "marketing/auth UI shell" → "auth and profile live; expenses still stubs")
- Update the architecture table if a path's role changed
- Update the "Learning-step placeholders" note if a route finished
  (remove the step from the unfinished list)
- Keep commands, conventions, and stack notes accurate

### `.claude/specs/<step>-<slug>.md`

- Tick every Definition-of-done item that is now true: `- [x]`
- Leave items unticked only if genuinely not done — if several are not done,
  the step is incomplete; **stop and tell the user**
- Add a one-line status under the title if useful:
  `> **Status:** implemented on <branch> — see .claude/plans/<step>-<slug>.md`

### `.claude/plans/<step>-<slug>.md`

- If the plan is still a proposal, mark it implemented:
  `> **Status:** implemented — verify with the checklist below`
- Do not delete the plan; it is the verification record

### Other docs

- `README.md` / `docs/` only if the diff makes them wrong
- Never invent docs the project does not have

Do **not** update docs for steps that were not part of this implementation.

---

## Step 4 — Group by theme and write the commit message

**Default: one commit.** The message names the theme of the whole change set,
not a file-by-file list.

Theme = the step or the single product change (e.g. `Step 4: profile page
dashboard`), not "updated app.py and style.css".

### Message format

Follow existing history (`Step 3: login, logout, sessions, and login_required`,
`Added login functionality`, `docs: apply review feedback to login-logout spec`):

```
<Scope>: <short imperative summary>

<optional body: 2-5 bullets on what landed and how to verify>
```

- **Scope** is the step or area: `Step 4`, `docs`, `landing`, `database`
- Imperative mood, no trailing period on the subject line
- Keep subject ≤ 72 characters
- Do **not** include `Co-Authored-By` or `Generated with` trailers

Examples of a good themed message:

```
Step 4: profile page dashboard and session hardening
```

```
docs: sync CLAUDE.md and Step 4 spec with shipped profile page
```

### When to split (only if themes are truly distinct)

If — and only if — the tree holds two unrelated themes (e.g. a finished
profile page **and** an unrelated typo fix in seed scripts), make **one
commit per theme**, each staged by path:

```bash
git add app.py templates/ static/css/style.css .claude/specs/04-profile-page.md
git commit -m "Step 4: profile page dashboard and session hardening"

git add scripts/seed_one_user.py
git commit -m "scripts: fix typo in seed_one_user"
```

Never split one logical step across commits. Never mix two steps into one.

---

## Step 5 — Stage and commit

```bash
git add <explicit paths from the diff>
git status -sb
git commit -m "<themed message>"
```

Rules:

- **Stage explicitly** — list the paths. Do not `git add -A` / `git add .`
  unless the user asked for it; never stage `venv/`, `expense_tracker.db`,
  `.env`, `__pycache__/`, or anything in `.gitignore`
- Stage docs and code **together** in the same commit when they ship the
  same theme (spec + implementation belong together)
- Do **not** use `--no-verify`
- Do **not** amend a commit that is already on the remote
- If a pre-commit hook fails, fix the cause; do not bypass it

Then confirm:

```bash
git log -1 --stat
```

---

## Step 6 — Push to the current remote branch

Push the branch you are on to its upstream of the same name. Do not switch
branches. Do not create a PR unless asked.

```bash
git push -u origin HEAD
```

- `-u` sets upstream on the first push of a new branch
- If the remote has moved, **stop** and show the user:

  ```bash
  git fetch origin
  git log --oneline HEAD..@{u}
  ```

  Do not force-push. Suggest `git pull --rebase origin <branch>` and ask
  before rebasing.

If the user asked for a PR as well, open it after the push — not instead of it.

---

## Step 7 — Report

Print exactly:

```
Branch:  <branch>
Commit:  <short-sha> <subject>
Pushed:  origin/<branch>
Docs:    <files updated, or "none needed">
```

Then list any Definition-of-done items left unticked (if any), and stop.
Do not start the next step unless asked.

---

## Hard rules

- Never commit `venv/`, `expense_tracker.db`, `.env`, or `.DS_Store`
- Never force-push
- Never rewrite history that has been pushed
- Never push to `main` / `master` unless the user is already on it and said so
- Docs in this commit must match the code in this commit
- One theme = one commit message. A file list is not a theme
- If the implementation is incomplete, refuse to ship and name the gaps
- If `git status` shows unexpected files (editor junk, exports), ask before
  staging them

## Troubleshooting

| Symptom | Fix |
|---|---|
| `error: src refspec HEAD does not match any` | No commits on this branch yet — commit first |
| `! [rejected] ... non-fast-forward` | Remote moved — `git fetch`, show the gap, ask before `pull --rebase` |
| `Please tell me who you are` | `git config user.name` / `user.email` — ask the user for values |
| Spec checklist half-ticked after reading | Implementation is incomplete — do not ship |
| `git add` picks up junk | Stage explicit paths only; add ignores to `.gitignore` if recurring |
