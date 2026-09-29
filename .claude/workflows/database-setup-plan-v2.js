export const meta = {
  name: 'database-setup-plan-v2',
  description: 'Draft and adversarially verify a v2 implementation plan for the database-setup spec',
  phases: [
    { title: 'Understand', detail: 'Spec extraction, code audit, and project conventions' },
    { title: 'Draft', detail: 'Three independent plan drafts from different angles' },
    { title: 'Verify', detail: 'Three adversarial lenses across all drafts' },
    { title: 'Synthesize', detail: 'Merge into the final plan document' },
  ],
}

const UNDERSTAND_SCHEMA = {
  type: 'object',
  properties: {
    summary: { type: 'string' },
    key_points: { type: 'array', items: { type: 'string' } },
    risks: { type: 'array', items: { type: 'string' } },
  },
  required: ['summary', 'key_points', 'risks'],
}

const VERDICT_SCHEMA = {
  type: 'object',
  properties: {
    lens: { type: 'string' },
    drafts: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          draft_id: { type: 'string' },
          scores: {
            type: 'object',
            properties: {
              spec_coverage: { type: 'number' },
              correctness: { type: 'number' },
              actionability: { type: 'number' },
              clarity: { type: 'number' },
            },
            required: ['spec_coverage', 'correctness', 'actionability', 'clarity'],
          },
          issues: { type: 'array', items: { type: 'string' } },
          strengths: { type: 'array', items: { type: 'string' } },
        },
        required: ['draft_id', 'scores', 'issues', 'strengths'],
      },
    },
    cross_draft_notes: { type: 'array', items: { type: 'string' } },
  },
  required: ['lens', 'drafts', 'cross_draft_notes'],
}

phase('Understand')
log('Reading the spec, current code, and project conventions')

const understand = await parallel([
  () => agent(
    'Read .claude/specs/01-database-setup.md in full (Spendly personal expense tracker — Step 1, database setup). Extract a complete, checkable requirements inventory. Cover: (a) database schema — every table, column, type, and constraint (including UNIQUE and FOREIGN KEY) exactly as specified; (b) function contracts for get_db(), init_db(), seed_db() including connection settings (row_factory, PRAGMA foreign_keys) and seed rules (demo user credentials, 8 sample expenses, category coverage, date spread across the current month, no duplicates on re-run); (c) app.py changes (imports, calling init_db() and seed_db() at startup inside app_context); (d) implementation rules (no ORM, parameterized queries only, no string-formatted SQL, REAL amounts, werkzeug password hashing, YYYY-MM-DD dates) and error-handling expectations; (e) the fixed 7-category list verbatim; (f) the Definition of Done checklist. Return ONLY structured data: a summary, one key_points entry per requirement (prefix each with its spec section number), and risks you notice in the spec itself. Do NOT write an implementation plan.',
    { label: 'spec-extract', phase: 'Understand', schema: UNDERSTAND_SCHEMA }
  ),
  () => agent(
    'Read database/db.py and app.py in the repository root (Spendly: a Flask + stdlib sqlite3 expense tracker). Also read .claude/specs/01-database-setup.md to compare against. Report the CURRENT state: which spec requirements the existing code already satisfies, which are missing or stubbed, and any deviations or defects (schema mismatches, missing constraints, connection lifecycle issues, date-handling edge cases, seeding logic, startup wiring). Quote exact function names and give file:line references. Flag anything risky even if it appears to work. Return ONLY structured data (summary, key_points, risks). Do NOT write an implementation plan.',
    { label: 'code-audit', phase: 'Understand', schema: UNDERSTAND_SCHEMA }
  ),
  () => agent(
    'Read requirements.txt, .gitignore, and the repository top-level layout (database/, templates/, static/, docs/, .claude/). Summarize facts that an implementation plan for the database step must respect: pinned dependencies (and that the spec forbids adding new pip packages), the SQLite DB file name and whether it is git-ignored, how the app is run in this Windows environment (the py launcher), package layout for imports (database/ package with __init__.py), and repository conventions about where specs and plans live. Use the project conventions already provided in your context rather than re-reading them. Return ONLY structured data (summary, key_points, risks). Do NOT write an implementation plan.',
    { label: 'conventions', phase: 'Understand', schema: UNDERSTAND_SCHEMA }
  ),
])

const ctx = understand.filter(Boolean)
if (ctx.length < 3) log('warning: only ' + ctx.length + '/3 understand agents returned')
const ctxJson = JSON.stringify(ctx)

phase('Draft')
log('Three independent plan drafts: spec-literal, risk-first, minimal-diff')

const ANGLES = [
  {
    id: 'spec-literal',
    angle: 'Walk through the spec section by section in spec order. Every spec section must map to at least one plan step, and the plan should make that mapping visible (e.g. "covers section 5B").',
  },
  {
    id: 'risk-first',
    angle: 'Order the steps by risk: data integrity and constraints first (PRAGMA foreign_keys on every connection, UNIQUE email, FOREIGN KEY enforcement, REAL amounts), then schema creation, then idempotent seeding, then app startup wiring, then verification. Call out failure modes explicitly for each step.',
  },
  {
    id: 'minimal-diff',
    angle: 'Smallest correct change set: exact function signatures, exact SQL statement strings, and the exact app.py edit. Prefer the fewest lines that fully satisfy the spec, including copy-pasteable code sketches.',
  },
]

const drafts = (await parallel(ANGLES.map((a, i) => () =>
  agent(
    'You are drafting ONE implementation plan for Spendly Step 1 (database setup). Angle for this draft: ' + a.angle + '\n\n' +
    'Base it on the spec at .claude/specs/01-database-setup.md and the current database/db.py and app.py — read those files yourself for exact details.\n\n' +
    'Analysis from a prior reading pass (JSON): ' + ctxJson + '\n\n' +
    'Your plan document MUST:\n' +
    '- Start with the H1: # Database Setup — Implementation Plan (' + a.id + ')\n' +
    '- Have sections: Context (one short paragraph), Current State vs Spec, Implementation Steps (numbered; each step names the files, functions, and SQL/code sketches), Seed Data (a table of the 8 sample expenses with amount/category/date/description), Verification (concrete commands with expected results, including the UNIQUE-constraint and FOREIGN-KEY failure cases), Definition of Done mapping, Risks and Edge Cases.\n' +
    '- Ground every claim in the actual spec text; include the exact schema DDL you would use.\n' +
    '- Respect the environment: Windows, run the app with the py launcher, DB file is expense_tracker.db in the project root, no new pip packages.\n' +
    '- Mark steps the current code already satisfies as "already present" rather than restating work to redo.\n' +
    '- Be executable-concise: no padding, no marketing language.\n' +
    'Return ONLY the markdown document. Your final message is the return value, not a chat reply.',
    { label: 'draft-' + a.id, phase: 'Draft' }
  ).then(text => ({ id: a.id, text }))
))).filter(Boolean)

if (drafts.length < 3) log('warning: only ' + drafts.length + '/3 drafts returned')
const draftsJson = JSON.stringify(drafts)

phase('Verify')
log('Adversarial review: spec coverage, technical correctness, actionability')

const LENSES = [
  {
    id: 'spec-coverage',
    desc: 'Check every spec requirement and every Definition of Done item against each draft. Flag anything missing, underspecified, or contradicted. Specifically verify: the two tables and all columns/constraints, the 7 categories verbatim, 8 sample expenses, demo user credentials and hashing, YYYY-MM-DD dates, parameterized queries only, no ORM, PRAGMA foreign_keys on every connection, UNIQUE email, FK enforcement, idempotent seed (no duplicates on re-run), and the app_context startup wiring in app.py.',
  },
  {
    id: 'technical-correctness',
    desc: 'Verify technical claims for runtime correctness: exact SQLite DDL (AUTOINCREMENT, DEFAULT datetime(\'now\'), FOREIGN KEY clause placement), sqlite3.Row behavior, when PRAGMA foreign_keys applies (it is per-connection), werkzeug.security.generate_password_hash usage and import path, whether Flask app_context is needed for startup init, date arithmetic edge cases (hardcoded day-of-month values — e.g. day 26 is safe in every month, day 30 is not), REAL vs INTEGER storage for amount, and SQL injection safety. Flag anything that would fail at runtime or violate the spec rules.',
  },
  {
    id: 'actionability',
    desc: 'Can an implementer execute each step on Windows with the py launcher without guessing? Are the verification steps concrete commands with expected outputs, including UNIQUE-constraint and FOREIGN-KEY failure cases? Is every Definition of Done item covered by some verification step? Flag vague steps, missing files, unverifiable claims, and any step that silently assumes something the spec does not state.',
  },
]

const verdicts = (await parallel(LENSES.map(l => () =>
  agent(
    'You are an ADVERSARIAL reviewer of implementation plans. Lens: ' + l.desc + '\n\n' +
    'Your job is to find flaws, not to praise. Try to refute the drafts. Default to flagging uncertainty as an issue.\n\n' +
    'Ground your review in the actual sources: read .claude/specs/01-database-setup.md, database/db.py, and app.py in the repository root.\n\n' +
    'Drafts to review (JSON array of {id, text}): ' + draftsJson + '\n\n' +
    'For EACH draft return: draft_id; scores as integers 1-10 for spec_coverage, correctness, actionability, clarity; issues (specific and concrete — each issue names what is wrong and what the spec or code actually says); strengths (only what is genuinely strong). Also cross_draft_notes: which draft is strongest overall and why, plus the single best idea from each draft worth keeping.\n' +
    'Return ONLY structured data. Do NOT write a plan.',
    { label: 'verify-' + l.id, phase: 'Verify', schema: VERDICT_SCHEMA }
  )
))).filter(Boolean)

const verdictsJson = JSON.stringify(verdicts)

phase('Synthesize')
log('Merging into the final v2 plan document')

const plan = await agent(
  'You are synthesizing the FINAL implementation plan document for Spendly Step 1 (database setup). It will be saved verbatim as .claude/plans/01-database-setup-v2.md in the project.\n\n' +
  'Inputs — prior analysis (JSON): ' + ctxJson + '\n\n' +
  'Drafts (JSON): ' + draftsJson + '\n\n' +
  'Adversarial verdicts (JSON): ' + verdictsJson + '\n\n' +
  'Instructions:\n' +
  '- Produce one polished markdown document that is better than every draft: take the strongest structure, keep every genuinely good idea from the verdicts (strengths and cross_draft_notes), and FIX every real issue that was raised. Discard nitpicks that are factually wrong.\n' +
  '- Double-check any claim you carry over by reading .claude/specs/01-database-setup.md, database/db.py, and app.py yourself. Where the current code already satisfies the spec, say so ("already present") instead of restating work to redo.\n' +
  '- Exact structure: "# Spendly Step 1 — Database Setup Implementation Plan (v2)" then "## Context", "## Current State vs Spec", "## Requirements Summary", "## Implementation Plan" (numbered steps with file paths, exact function contracts, and SQL DDL sketches), "## Seed Data" (table of the 8 sample expenses: amount, category, date, description), "## Verification" (commands with expected results, including UNIQUE and FOREIGN KEY failure cases), "## Definition of Done" (checkbox list, each item mapped to the verification step that proves it), "## Risks and Edge Cases", "## Notes" (state that this supersedes .claude/plans/01-database-setup.md).\n' +
  '- Tone: an executable engineering plan for a step-by-step learning project. Concise, concrete, no filler.\n' +
  '- Windows environment: run with the py launcher; DB file is expense_tracker.db in the project root; no new pip packages.\n' +
  'Return ONLY the markdown document, starting with the H1 line. Your final message is the return value, not a chat reply.',
  { label: 'synthesize-plan', phase: 'Synthesize' }
)

return { plan, drafts, verdicts, understand: ctx }