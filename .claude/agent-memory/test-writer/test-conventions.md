---
name: test-conventions
description: How Spendly tests are written — fixed-date sample data, text-scrape UI asserts, spec-quoted copy is contract, naming
metadata:
  type: project
---

Conventions for Spendly pytest suites (validated in `tests/test_06-data-filter-for-profile-page.py`).

- Naming: `tests/test_<step>-<kebab-feature>.py` (hyphenated module names collect fine under pytest 8), test names spell the requirement, e.g. `test_reversed_date_range_shows_error_and_unfiltered_snapshot`.
- Deterministic sample data: replicate the spec's demo numbers (8 expenses / ₹248.24, Food = 12.50 + 18.75) on **fixed** ISO dates (2026-09-02 … 2026-09-26) so DoD figures match without depending on `date.today()`. Helpers: `_insert_user` (werkzeug hash) + `_insert_expense` with explicit commit, login via `POST /login`.
- Assert HTML by visible content (money strings `₹%.2f`, description text, spec-quoted copy) or tiny regexes over tag-stripped text — not CSS classes. Gotcha: strip-tags leaves 10+ gap chars between label and value spans; collapse whitespace (`re.sub(r"\s+", " ", ...)`) before matching `Expenses <n>`.
- Spec-quoted UI copy is testable contract: "No expenses yet", "No expenses match these filters", "No transactions yet", "Filtered by …", "Clear filters", "All categories". Responsive (≤600px) and `git diff` hex-colour checks are NOT pytest-testable — report uncovered instead.
- Count on the page is awkward (bare number in a stat card); use API `expense_count` for exact counts and page money/description strings for panel filtering.
- **Why:** these choices keep tests readable, order-free, and faithful to the spec instead of the implementation.
- **How to apply:** reuse the same sample/helpers when testing expense CRUD (Steps 7–9); keep `WHERE user_id` isolation cases (two users + `?user_id=` injection) in every data-visibility feature. See [[test-infra-conftest]] and [[test-api-contracts]].
