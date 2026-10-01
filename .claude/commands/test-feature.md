---
description: Writes and runs tests for a specific Spendly feature. Pass the spec name as argument e.g. /test-feature 05-backend-routes-for-profile-page
argument-hint: "Spec name e.g. 05-backend-routes-for-profile-page"
allowed-tools: Read, Glob, Bash(py -m pytest)
---

Run the full testing pipeline for the feature specified
in $ARGUMENTS.

If no argument is provided, stop immediately and say:
"Please provide a spec name. Usage: /test-feature
<spec-name> e.g. /test-feature 05-backend-routes-for-profile-page"

If `.claude/specs/$ARGUMENTS.md` does not exist, stop
immediately and say:
"Spec file not found at .claude/specs/$ARGUMENTS.md.
Please check the spec name and try again."

---

## Step 1: Write Tests

Invoke the **test-writer** subagent with the following
context:

- Spec file to base tests on:
  `.claude/specs/$ARGUMENTS.md`
- Source files to read for structure only:
  - `app.py`
  - `database/` directory
- Output test file to create:
  `tests/test_$ARGUMENTS.py`
- Instruction: Write tests based on what the spec says
  the feature SHOULD do. Do NOT derive test logic from
  reading the implementation. Cover happy paths, edge
  cases, auth guards, validation errors, and DB side
  effects. Verify the new module before reporting, and
  leave implementation/spec mismatches failing.

Wait for test-writer to fully complete and confirm the
test file has been written before proceeding to Step 2.

---

## Step 2: Run Tests

Once test-writer has finished, invoke the
**test-runner** subagent with the following context:

- Test file to execute:
  `tests/test_$ARGUMENTS.py`
- Spec file for context:
  `.claude/specs/$ARGUMENTS.md`
- Source files to analyze against when diagnosing
  failures:
  - `app.py`
  - `database/` directory
- Run command:
  `py -m pytest tests/test_$ARGUMENTS.py -v`
- Instruction: Run ONLY the specified test file. Do
  NOT run the full test suite. Scope the run to this
  feature and say so in the report. Analyze any failures
  by cross-referencing the test code, the spec, and the
  source files. Classify each failure as a test defect,
  an implementation/spec mismatch, shared state, a
  flake, or an environment blocker, and name an owner.

---

## Safety precondition

Both subagents must honour the database isolation rule:
`app.py` calls `init_db()` and `seed_db()` at module
import time, so the repository-root `conftest.py` has to
repoint `database.db.DB_PATH` at a temporary path before
`app` is imported. If that guard is missing or unclear,
do not run anything — report the pipeline as blocked by
unsafe database isolation and stop. Never let a run touch
the real `expense_tracker.db`.

---

## Handoff Rules

- Do NOT start Step 2 until Step 1 is fully complete
- Do NOT attempt to fix any code regardless of what
  the test results show
- Do NOT run any tests beyond `tests/test_$ARGUMENTS.py`
- If test-writer reports it could not write
  the test file, stop and report the reason — do NOT
  proceed to Step 2
- If test-writer reports a required spec case as blocked
  or ambiguous, carry that into the final output rather
  than silently dropping it

---

## Final Output

After both subagents complete, produce a combined
summary:

### Testing Pipeline Report — $ARGUMENTS

**Step 1 — Tests Written**
- List each test written with a one-line description
  of which spec requirement it validates
- Note any spec cases left uncovered and why

**Step 2 — Test Results**
- Mirror the test-runner's structured report

**Verdict**
One of:
- ✅ Ready for code review — all tests pass
- ⚠️ Needs review — tests pass but spec cases were
  skipped as blocked or ambiguous
- ❌ Needs fixes — list the failing tests and their
  root causes
