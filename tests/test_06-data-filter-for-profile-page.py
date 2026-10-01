"""Tests for Step 06 — Data Filter for Profile Page.

Source of truth: .claude/specs/06-data-filter-for-profile-page.md

These tests seed their own deterministic data (fixed dates, fixed amounts that
mirror the documented demo sample) into the isolated temp database wired up by
the repository-root conftest.py. They never rely on seed_db() demo rows and
never touch the real expense_tracker.db.
"""

import re
from urllib.parse import urlparse

import pytest
from werkzeug.security import generate_password_hash


# ------------------------------------------------------------------ #
# Deterministic sample — same 8 rows / totals as the spec's demo data, #
# but on fixed ISO dates so tests never depend on today's date.       #
# ------------------------------------------------------------------ #

PASSWORD = "password123"

SAMPLE_EXPENSES = [
    (12.50, "Food", "2026-09-02", "Lunch at the cafe"),
    (45.00, "Transport", "2026-09-05", "Monthly bus pass top-up"),
    (60.00, "Bills", "2026-09-08", "Electricity bill"),
    (22.00, "Health", "2026-09-11", "Pharmacy purchase"),
    (30.00, "Entertainment", "2026-09-14", "Movie ticket"),
    (55.00, "Shopping", "2026-09-18", "New running shoes"),
    (4.99, "Other", "2026-09-22", "App subscription"),
    (18.75, "Food", "2026-09-26", "Groceries run"),
]

# Unfiltered totals from the spec's Definition of done.
TOTAL_ALL = 248.24
COUNT_ALL = 8
TOTAL_FOOD = 31.25
COUNT_FOOD = 2
TOTAL_FOOD_LUNCH_ONLY = 12.50


# ------------------------------------------------------------------ #
# Helpers                                                            #
# ------------------------------------------------------------------ #

def _insert_user(conn, name, email, password=PASSWORD):
    cur = conn.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
        (name, email, generate_password_hash(password)),
    )
    conn.commit()
    return cur.lastrowid


def _insert_expense(conn, user_id, amount, category, date, description):
    conn.execute(
        "INSERT INTO expenses (user_id, amount, category, date, description) "
        "VALUES (?, ?, ?, ?, ?)",
        (user_id, amount, category, date, description),
    )
    conn.commit()


def _login(client, email, password=PASSWORD):
    resp = client.post(
        "/login", data={"email": email, "password": password}, follow_redirects=False
    )
    assert resp.status_code == 302, f"login failed for {email}: {resp.status_code}"
    return resp


def _html(resp):
    return resp.get_data(as_text=True)


def _strip_tags(html):
    return re.sub(r"<[^>]+>", " ", html)


def _page_expense_count(html):
    """Expense-count stat value, read from visible text (markup-agnostic)."""
    text = re.sub(r"\s+", " ", _strip_tags(html))
    m = re.search(r"Expenses\D{0,5}?(\d+)\b", text)
    return int(m.group(1)) if m else None


def _input_tag(html, name):
    for tag in re.findall(r"<input\b[^>]*>", html):
        if re.search(rf'name="{re.escape(name)}"', tag):
            return tag
    return ""


def _input_value(html, name):
    m = re.search(r'value="([^"]*)"', _input_tag(html, name))
    return m.group(1) if m else ""


def _selected_option_label(html):
    """Text of the <option> carrying `selected`, or None when none is selected."""
    for tag in re.findall(r"<option\b[^>]*>.*?</option>", html, re.DOTALL):
        if re.search(r"\bselected\b", tag):
            return re.sub(r"<[^>]+>", "", tag).strip()
    return None


def _clear_filters_hrefs(html):
    hrefs = []
    for tag in re.findall(r"<a\b[^>]*>.*?</a>", html, re.DOTALL):
        text = re.sub(r"<[^>]+>", "", tag).strip().lower()
        if text == "clear filters":
            m = re.search(r'href="([^"]*)"', tag)
            if m:
                hrefs.append(m.group(1))
    return hrefs


def _filtered_by_text(html):
    """Contents of the 'Filtered by …' summary line (empty string when absent)."""
    m = re.search(r"Filtered by([^<]*)", html)
    return m.group(1) if m else ""


def _assert_unfiltered_page(html):
    """The no-filter /profile snapshot: full sample total, count, breakdown."""
    assert "₹248.24" in html
    assert _page_expense_count(html) == COUNT_ALL
    for amount in ("₹60.00", "₹45.00", "₹31.25", "₹30.00", "₹22.00", "₹4.99", "₹55.00"):
        assert amount in html, f"breakdown total {amount} missing from unfiltered page"


def _assert_category_options(html, categories):
    assert 'name="category"' in html
    assert "All categories" in html
    for cat in categories:
        assert re.search(
            rf"<option\b[^>]*value=\"{re.escape(cat)}\"", html
        ), f"category option {cat!r} missing"


# ------------------------------------------------------------------ #
# Fixtures                                                           #
# ------------------------------------------------------------------ #

@pytest.fixture()
def clean(db_conn):
    """Empty users + expenses so seed_db() demo rows never leak into a test."""
    db_conn.execute("DELETE FROM expenses")
    db_conn.execute("DELETE FROM users")
    db_conn.commit()
    return db_conn


@pytest.fixture()
def alice(clean):
    """User with the 8 sample expenses on fixed dates. Returns her user id."""
    user_id = _insert_user(clean, "Alice", "alice@example.com")
    for amount, category, date, description in SAMPLE_EXPENSES:
        _insert_expense(clean, user_id, amount, category, date, description)
    return user_id


@pytest.fixture()
def alice_client(client, alice):
    _login(client, "alice@example.com")
    return client


@pytest.fixture()
def empty_client(client, clean):
    """Signed-in user with zero expenses, for the no-expenses-yet state."""
    _insert_user(clean, "Carol", "carol@example.com")
    _login(client, "carol@example.com")
    return client


# ------------------------------------------------------------------ #
# Filter bar / form controls                                          #
# ------------------------------------------------------------------ #

def test_profile_filter_bar_offers_all_categories_and_date_inputs(alice_client):
    """/profile shows a filter bar: All + the 7 CATEGORIES, and date_from/date_to."""
    from database.db import CATEGORIES

    html = _html(alice_client.get("/profile"))
    _assert_category_options(html, CATEGORIES)
    assert 'name="date_from"' in html
    assert 'name="date_to"' in html
    assert _input_tag(html, "date_from")
    assert _input_tag(html, "date_to")


def test_active_filter_summary_and_form_reflect_submitted_values(alice_client):
    """'Filtered by …' names category + dates as entered; controls keep values."""
    html = _html(
        alice_client.get(
            "/profile?category=Food&date_from=2026-09-01&date_to=2026-09-30"
        )
    )
    summary = _filtered_by_text(html)
    assert summary, "expected a 'Filtered by …' summary when filters are active"
    assert "Food" in summary
    assert "2026-09-01" in summary
    assert "2026-09-30" in summary

    assert _selected_option_label(html) == "Food"
    assert _input_value(html, "date_from") == "2026-09-01"
    assert _input_value(html, "date_to") == "2026-09-30"


def test_clear_filters_link_targets_bare_route_and_restores_unfiltered(alice_client):
    """'Clear filters' links to the bare route; following it empties controls."""
    html = _html(alice_client.get("/profile?category=Food"))
    hrefs = _clear_filters_hrefs(html)
    assert hrefs, "expected a 'Clear filters' link on the filtered profile page"
    bare = [h for h in hrefs if "?" not in h and urlparse(h).path == "/profile"]
    assert bare, f"Clear filters must link to /profile with no query string, got {hrefs}"

    resp = alice_client.get(bare[0])
    assert resp.status_code == 200
    cleared = _html(resp)
    _assert_unfiltered_page(cleared)
    label = _selected_option_label(cleared)
    assert label is None or label.lower().startswith("all")
    assert _input_value(cleared, "date_from") == ""
    assert _input_value(cleared, "date_to") == ""
    assert _filtered_by_text(cleared) == ""


# ------------------------------------------------------------------ #
# Unfiltered snapshot (nothing applied)                               #
# ------------------------------------------------------------------ #

def test_profile_without_filters_shows_unfiltered_snapshot(alice_client):
    """DoD: no filters → 8 expenses, ₹248.24, full breakdown Bills ₹60.00 … Other ₹4.99."""
    html = _html(alice_client.get("/profile"))
    _assert_unfiltered_page(html)
    assert "₹60.00" in html  # Bills
    assert "₹4.99" in html  # Other
    # Recent transactions (newest 5) are unfiltered too.
    for desc in (
        "Groceries run",
        "App subscription",
        "New running shoes",
        "Movie ticket",
        "Pharmacy purchase",
    ):
        assert desc in html
    assert _filtered_by_text(html) == ""


def test_api_without_filters_returns_full_sample(alice_client):
    """Unfiltered JSON baseline: helpers' defaults preserve current behaviour."""
    stats = alice_client.get("/api/profile/stats").get_json()
    assert stats["expense_count"] == COUNT_ALL
    assert stats["total_spend"] == pytest.approx(TOTAL_ALL)

    breakdown = alice_client.get("/api/profile/breakdown").get_json()["breakdown"]
    by_cat = {row["category"]: row for row in breakdown}
    assert set(by_cat) == {
        "Food",
        "Transport",
        "Bills",
        "Health",
        "Entertainment",
        "Shopping",
        "Other",
    }
    assert by_cat["Bills"]["total"] == pytest.approx(60.00)
    assert by_cat["Bills"]["bar_pct"] == pytest.approx(100.0)
    assert by_cat["Food"]["total"] == pytest.approx(TOTAL_FOOD)
    assert by_cat["Other"]["total"] == pytest.approx(4.99)

    history = alice_client.get("/api/profile/history").get_json()
    assert history["count"] == COUNT_ALL


# ------------------------------------------------------------------ #
# Category filter                                                     #
# ------------------------------------------------------------------ #

def test_profile_category_filter_shows_only_food(alice_client):
    """DoD: category=Food → 2 expenses, ₹31.25, only Food rows/bars."""
    html = _html(alice_client.get("/profile?category=Food"))
    assert "₹31.25" in html
    assert _page_expense_count(html) == COUNT_FOOD
    assert "Lunch at the cafe" in html
    assert "Groceries run" in html
    # Row amounts of the two Food expenses are shown.
    assert "₹12.50" in html
    assert "₹18.75" in html
    # Other categories' breakdown totals / rows must not appear.
    for other in ("₹60.00", "₹45.00", "₹22.00", "₹30.00", "₹55.00", "₹4.99"):
        assert other not in html, f"{other} belongs outside the Food filter"
    assert "Electricity bill" not in html
    assert "Movie ticket" not in html


def test_api_category_filter_matches_profile_page(alice_client):
    """DoD: /api/profile/*?category=Food returns the same Food numbers as the page."""
    stats = alice_client.get("/api/profile/stats?category=Food").get_json()
    assert stats["expense_count"] == COUNT_FOOD
    assert stats["total_spend"] == pytest.approx(TOTAL_FOOD)

    page = _html(alice_client.get("/profile?category=Food"))
    assert "₹31.25" in page  # total the page shows for Food

    breakdown = alice_client.get("/api/profile/breakdown?category=Food").get_json()[
        "breakdown"
    ]
    assert len(breakdown) == 1
    assert breakdown[0]["category"] == "Food"
    assert breakdown[0]["count"] == COUNT_FOOD
    assert breakdown[0]["total"] == pytest.approx(TOTAL_FOOD)

    history = alice_client.get("/api/profile/history?category=Food").get_json()
    assert history["count"] == COUNT_FOOD
    descriptions = {row["description"] for row in history["transactions"]}
    assert descriptions == {"Lunch at the cafe", "Groceries run"}


def test_category_filter_breakdown_shows_only_filtered_category(alice_client):
    """Rule: breakdown must not un-group into other categories; bar_pct vs filtered max."""
    breakdown = alice_client.get("/api/profile/breakdown?category=Food").get_json()[
        "breakdown"
    ]
    assert [row["category"] for row in breakdown] == ["Food"]
    assert breakdown[0]["bar_pct"] == pytest.approx(100.0)


# ------------------------------------------------------------------ #
# Date range + AND logic                                              #
# ------------------------------------------------------------------ #

def test_date_range_is_inclusive_on_both_ends(alice_client):
    """date_from/date_to inclusive (>= / <=): a single-day range keeps that day."""
    stats = alice_client.get(
        "/api/profile/stats?date_from=2026-09-02&date_to=2026-09-02"
    ).get_json()
    assert stats["expense_count"] == 1
    assert stats["total_spend"] == pytest.approx(12.50)

    stats = alice_client.get(
        "/api/profile/stats?date_from=2026-09-26&date_to=2026-09-26"
    ).get_json()
    assert stats["expense_count"] == 1
    assert stats["total_spend"] == pytest.approx(18.75)


def test_date_range_covers_only_first_sample_expense(alice_client):
    """DoD: a range covering only the Food ₹12.50 row → 1 expense and that total."""
    html = _html(
        alice_client.get("/profile?date_from=2026-09-01&date_to=2026-09-03")
    )
    assert "₹12.50" in html
    assert _page_expense_count(html) == 1
    for desc in (
        "Monthly bus pass top-up",
        "Electricity bill",
        "Pharmacy purchase",
        "Movie ticket",
        "New running shoes",
        "App subscription",
        "Groceries run",
    ):
        assert desc not in html

    stats = alice_client.get(
        "/api/profile/stats?date_from=2026-09-01&date_to=2026-09-03"
    ).get_json()
    assert stats["expense_count"] == 1
    assert stats["total_spend"] == pytest.approx(TOTAL_FOOD_LUNCH_ONLY)


def test_single_sided_date_filters(alice_client):
    """date_from only bounds the start; date_to only bounds the end."""
    # from 09-18: shoes (09-18) + app subscription (09-22) + groceries (09-26)
    stats = alice_client.get("/api/profile/stats?date_from=2026-09-18").get_json()
    assert stats["expense_count"] == 3
    assert stats["total_spend"] == pytest.approx(55.00 + 4.99 + 18.75)

    stats = alice_client.get("/api/profile/stats?date_to=2026-09-02").get_json()
    assert stats["expense_count"] == 1
    assert stats["total_spend"] == pytest.approx(12.50)


def test_category_and_date_range_combine_with_and_logic(alice_client):
    """DoD: Food in a range holding only the lunch → exactly that one row."""
    html = _html(
        alice_client.get(
            "/profile?category=Food&date_from=2026-09-01&date_to=2026-09-03"
        )
    )
    assert "Lunch at the cafe" in html
    assert "Groceries run" not in html
    assert _page_expense_count(html) == 1

    stats = alice_client.get(
        "/api/profile/stats?category=Food&date_from=2026-09-01&date_to=2026-09-03"
    ).get_json()
    assert stats["expense_count"] == 1
    assert stats["total_spend"] == pytest.approx(TOTAL_FOOD_LUNCH_ONLY)

    history = alice_client.get(
        "/api/profile/history?category=Food&date_from=2026-09-01&date_to=2026-09-03"
    ).get_json()
    assert history["count"] == 1
    assert history["transactions"][0]["description"] == "Lunch at the cafe"


def test_all_panels_honour_the_same_filters(alice_client):
    """DoD: totals, count, breakdown and recent/history all reflect one filter."""
    query = "date_from=2026-09-02&date_to=2026-09-08"  # lunch, bus pass, electricity
    expected_total = 12.50 + 45.00 + 60.00  # 117.50

    page = _html(alice_client.get(f"/profile?{query}"))
    assert "₹117.50" in page
    assert _page_expense_count(page) == 3
    for desc in ("Lunch at the cafe", "Monthly bus pass top-up", "Electricity bill"):
        assert desc in page
    for desc in ("Pharmacy purchase", "Movie ticket", "New running shoes",
                 "App subscription", "Groceries run"):
        assert desc not in page
    for excluded in ("₹22.00", "₹30.00", "₹55.00", "₹4.99", "₹18.75"):
        assert excluded not in page, f"{excluded} is outside the filtered panels"

    stats = alice_client.get(f"/api/profile/stats?{query}").get_json()
    assert stats["expense_count"] == 3
    assert stats["total_spend"] == pytest.approx(expected_total)

    breakdown = alice_client.get(f"/api/profile/breakdown?{query}").get_json()[
        "breakdown"
    ]
    assert {row["category"] for row in breakdown} == {"Food", "Transport", "Bills"}
    assert sum(row["count"] for row in breakdown) == 3
    assert sum(row["total"] for row in breakdown) == pytest.approx(expected_total)

    history = alice_client.get(f"/api/profile/history?{query}").get_json()
    assert history["count"] == 3
    assert {row["description"] for row in history["transactions"]} == {
        "Lunch at the cafe",
        "Monthly bus pass top-up",
        "Electricity bill",
    }


def test_breakdown_bar_pct_is_relative_to_filtered_largest_category(alice_client):
    """Bar percentages are relative to the largest category of the filtered set."""
    breakdown = alice_client.get(
        "/api/profile/breakdown?date_from=2026-09-02&date_to=2026-09-05"
    ).get_json()["breakdown"]
    by_cat = {row["category"]: row for row in breakdown}
    assert set(by_cat) == {"Food", "Transport"}
    assert by_cat["Transport"]["total"] == pytest.approx(45.00)
    assert by_cat["Transport"]["bar_pct"] == pytest.approx(100.0)
    # 12.50 / 45.00 of the filtered maximum
    assert by_cat["Food"]["bar_pct"] == pytest.approx(27.8, abs=0.1)


# ------------------------------------------------------------------ #
# /profile/history and /api/profile/history                           #
# ------------------------------------------------------------------ #

def test_profile_history_applies_the_same_filters(alice_client):
    """DoD: /profile/history accepts the same params and matches recent logic."""
    page = _html(alice_client.get("/profile/history?category=Food"))
    assert "Lunch at the cafe" in page
    assert "Groceries run" in page
    assert "Electricity bill" not in page
    assert "Movie ticket" not in page

    api = alice_client.get("/api/profile/history?category=Food").get_json()
    assert {row["description"] for row in api["transactions"]} == {
        "Lunch at the cafe",
        "Groceries run",
    }
    for row in api["transactions"]:
        assert row["category"] == "Food"
        assert row["description"] in page


def test_api_history_respects_limit_together_with_filters(alice_client):
    """`limit` still works in addition to the filter query params."""
    data = alice_client.get(
        "/api/profile/history?category=Food&limit=1"
    ).get_json()
    assert data["count"] == 1
    assert data["transactions"][0]["description"] == "Groceries run"  # newest first
    assert data["transactions"][0]["category"] == "Food"


# ------------------------------------------------------------------ #
# Invalid input handling                                              #
# ------------------------------------------------------------------ #

def test_empty_category_param_means_all_categories(alice_client):
    """`category` empty/missing means 'all'."""
    stats = alice_client.get("/api/profile/stats?category=").get_json()
    assert stats["expense_count"] == COUNT_ALL
    assert stats["total_spend"] == pytest.approx(TOTAL_ALL)


def test_unknown_category_is_ignored_not_treated_as_a_filter(alice_client):
    """A category outside CATEGORIES must not act as a filter (no zero-match)."""
    html = _html(alice_client.get("/profile?category=NotACategory"))
    assert html and "No expenses match these filters" not in html
    assert "₹248.24" in html  # invalid value ignored → unfiltered snapshot

    stats = alice_client.get("/api/profile/stats?category=NotACategory").get_json()
    assert stats["expense_count"] == COUNT_ALL
    assert stats["total_spend"] == pytest.approx(TOTAL_ALL)


@pytest.mark.parametrize(
    "bad_date",
    ["2026-9-2", "02/09/2026", "not-a-date", "2026-02-30"],
)
def test_malformed_dates_are_ignored_not_treated_as_filters(alice_client, bad_date):
    """Only YYYY-MM-DD is accepted; malformed input is ignored, never 500s."""
    stats = alice_client.get(
        f"/api/profile/stats?date_from={bad_date}"
    ).get_json()
    assert stats["expense_count"] == COUNT_ALL
    assert stats["total_spend"] == pytest.approx(TOTAL_ALL)

    stats = alice_client.get(f"/api/profile/stats?date_to={bad_date}").get_json()
    assert stats["expense_count"] == COUNT_ALL
    assert stats["total_spend"] == pytest.approx(TOTAL_ALL)


def test_malformed_date_on_page_renders_unfiltered_snapshot(alice_client):
    resp = alice_client.get("/profile?date_from=02/09/2026&date_to=whatever")
    assert resp.status_code == 200
    html = _html(resp)
    assert "No expenses match these filters" not in html
    assert "₹248.24" in html  # junk dates ignored


def test_reversed_date_range_shows_error_and_unfiltered_snapshot(alice_client):
    """DoD: date_from > date_to → friendly error + unfiltered snapshot (no swap)."""
    resp = alice_client.get("/profile?date_from=2026-09-20&date_to=2026-09-01")
    assert resp.status_code == 200
    html = _html(resp)
    text = _strip_tags(html).lower()
    assert "start date" in text and "end date" in text  # friendly range-order error

    # Unfiltered snapshot — not the swapped 09-01..09-09-20 subset (6 / ₹224.50)
    # and not a misleading empty set.
    assert "₹248.24" in html
    assert _page_expense_count(html) == COUNT_ALL
    assert "₹224.50" not in html
    assert "No expenses match these filters" not in html


def test_reversed_date_range_api_does_not_return_misleading_set(alice_client):
    """API must not apply reversed bounds or swap them: unfiltered or 4xx."""
    resp = alice_client.get(
        "/api/profile/stats?date_from=2026-09-20&date_to=2026-09-01"
    )
    if resp.status_code == 200:
        data = resp.get_json()
        assert data["expense_count"] == COUNT_ALL, "reversed range must not filter/swap"
        assert data["total_spend"] == pytest.approx(TOTAL_ALL)
    else:
        assert 400 <= resp.status_code < 500


# ------------------------------------------------------------------ #
# Three UI states: empty / no-match / filtered-with-data               #
# ------------------------------------------------------------------ #

def test_zero_matches_show_no_match_state_not_empty_state(alice_client):
    """DoD: filters matching nothing → no-match + clear link, not 'No expenses yet'."""
    html = _html(
        alice_client.get(
            "/profile?category=Food&date_from=2026-09-05&date_to=2026-09-05"
        )
    )
    assert "No expenses match these filters" in html
    assert "No expenses yet" not in html
    assert "₹0.00" not in html  # no zero-value breakdown bars
    hrefs = _clear_filters_hrefs(html)
    assert hrefs and any("?" not in h and urlparse(h).path == "/profile" for h in hrefs)
    # Filters are still named so the user can adjust them.
    summary = _filtered_by_text(html)
    assert "Food" in summary and "2026-09-05" in summary


def test_no_expenses_at_all_shows_empty_state_not_no_match(empty_client):
    """State 1 (nothing ever) is distinct from state 2 (filters match nothing)."""
    html = _html(empty_client.get("/profile"))
    assert "No expenses yet" in html
    assert "No expenses match these filters" not in html


def test_profile_history_zero_matches_show_no_match_state(alice_client):
    """/profile/history no-match state is not the 'No transactions yet' copy."""
    html = _html(
        alice_client.get(
            "/profile/history?category=Food&date_from=2026-09-05&date_to=2026-09-05"
        )
    )
    assert "No expenses match these filters" in html
    assert "No transactions yet" not in html
    hrefs = _clear_filters_hrefs(html)
    assert hrefs and any(
        "?" not in h and urlparse(h).path == "/profile/history" for h in hrefs
    )


def test_profile_history_no_expenses_shows_no_transactions_yet(empty_client):
    """History empty state (no expenses ever) stays distinct from the no-match copy."""
    html = _html(empty_client.get("/profile/history"))
    assert "No transactions yet" in html
    assert "No expenses match these filters" not in html


# ------------------------------------------------------------------ #
# Auth + user isolation                                               #
# ------------------------------------------------------------------ #

@pytest.mark.parametrize(
    "path",
    [
        "/profile?category=Food",
        "/profile?category=Food&date_from=2026-09-01&date_to=2026-09-30",
        "/profile/history?category=Food",
        "/api/profile/stats?category=Food",
        "/api/profile/breakdown?date_from=2026-09-01&date_to=2026-09-30",
        "/api/profile/history?category=Food&limit=5",
    ],
)
def test_signed_out_filtered_routes_redirect_to_login(client, path):
    """DoD: every filtered route stays behind @login_required."""
    resp = client.get(path)
    assert resp.status_code == 302
    assert urlparse(resp.headers["Location"]).path == "/login"


@pytest.mark.parametrize("path", ["/", "/login", "/register", "/terms"])
def test_public_pages_do_not_leak_filter_ui(client, path):
    """DoD: no filter UI leaks on public pages."""
    html = _html(client.get(path))
    assert 'name="date_from"' not in html
    assert 'name="date_to"' not in html
    assert "clear filters" not in html.lower()
    assert "Filtered by" not in html


def test_filters_never_widen_visibility_beyond_signed_in_user(db_conn, alice, alice_client):
    """Always WHERE user_id first: filters (and user_id params) never leak rows."""
    bob_id = _insert_user(db_conn, "Bob", "bob@example.com")
    _insert_expense(db_conn, bob_id, 99.99, "Food", "2026-09-02", "Bob secret dinner")

    stats = alice_client.get("/api/profile/stats?category=Food").get_json()
    assert stats["expense_count"] == COUNT_FOOD
    assert stats["total_spend"] == pytest.approx(TOTAL_FOOD)

    history = alice_client.get("/api/profile/history?category=Food").get_json()
    assert "Bob secret dinner" not in {row["description"] for row in history["transactions"]}

    page = _html(alice_client.get("/profile?category=Food"))
    assert "Bob secret dinner" not in page
    assert "₹99.99" not in page

    # user_id must come from the session only — never from the query string.
    injected = alice_client.get(f"/api/profile/stats?user_id={bob_id}").get_json()
    assert injected["expense_count"] == COUNT_ALL
    assert injected["total_spend"] == pytest.approx(TOTAL_ALL)


def test_second_users_filtered_numbers_exclude_other_users_rows(db_conn, alice, alice_client):
    """DoD: a second signed-in user's filtered numbers never include others' rows."""
    bob_id = _insert_user(db_conn, "Bob", "bob@example.com")
    _insert_expense(db_conn, bob_id, 99.99, "Food", "2026-09-02", "Bob secret dinner")
    _insert_expense(db_conn, bob_id, 5.00, "Food", "2026-09-20", "Bob snack")

    alice_client.get("/logout")
    _login(alice_client, "bob@example.com")

    stats = alice_client.get("/api/profile/stats?category=Food").get_json()
    assert stats["expense_count"] == 2
    assert stats["total_spend"] == pytest.approx(104.99)

    history = alice_client.get("/api/profile/history?category=Food").get_json()
    descriptions = {row["description"] for row in history["transactions"]}
    assert descriptions == {"Bob secret dinner", "Bob snack"}
    assert "Lunch at the cafe" not in descriptions

    page = _html(alice_client.get("/profile?category=Food"))
    assert "Lunch at the cafe" not in page
    assert "₹31.25" not in page


# ------------------------------------------------------------------ #
# Spec invariants: no schema change, other routes unaffected          #
# ------------------------------------------------------------------ #

def test_expenses_schema_has_no_new_columns(db_conn):
    """Spec: 'No database changes' — expenses keeps the Step 1 columns only."""
    cols = [
        row["name"]
        for row in db_conn.execute("PRAGMA table_info(expenses)").fetchall()
    ]
    assert cols == [
        "id",
        "user_id",
        "amount",
        "category",
        "date",
        "description",
        "created_at",
    ]


def test_unrelated_routes_still_work(app, alice_client):
    """DoD: the filter step leaves /, auth, terms and account routes working."""
    signed_out = app.test_client()  # fresh session — not the logged-in client
    for path in ("/", "/terms", "/register", "/login"):
        assert signed_out.get(path).status_code == 200

    assert alice_client.get("/profile/edit").status_code == 200
    assert alice_client.get("/profile/password").status_code == 200
    resp = alice_client.get("/logout")
    assert resp.status_code == 302
    assert urlparse(resp.headers["Location"]).path == "/"
