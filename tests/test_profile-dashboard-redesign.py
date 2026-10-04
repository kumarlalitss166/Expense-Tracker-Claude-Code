"""Tests for the profile dashboard redesign.

Covers the new presentation metrics (average spend, top category, share %),
the app shell, INR formatting, and the safety contracts the redesign must
not weaken (user isolation, POST-only delete, escaping).
"""

import re
from urllib.parse import urlparse

import pytest
from werkzeug.security import generate_password_hash


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

TOTAL_ALL = 248.24
COUNT_ALL = 8
AVG_ALL = TOTAL_ALL / COUNT_ALL  # 31.03


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
    assert resp.status_code == 302
    return resp


def _html(resp):
    return resp.get_data(as_text=True)


def _text(html):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html))


@pytest.fixture()
def clean(db_conn):
    db_conn.execute("DELETE FROM expenses")
    db_conn.execute("DELETE FROM users")
    db_conn.commit()
    return db_conn


@pytest.fixture()
def alice(clean):
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
    _insert_user(clean, "Carol", "carol@example.com")
    _login(client, "carol@example.com")
    return client


# ------------------------------------------------------------------ #
# New dashboard metrics                                              #
# ------------------------------------------------------------------ #

def test_api_stats_include_average_spend(alice_client):
    stats = alice_client.get("/api/profile/stats").get_json()
    assert stats["average_spend"] == pytest.approx(AVG_ALL)


def test_api_stats_average_is_zero_without_expenses(empty_client):
    stats = empty_client.get("/api/profile/stats").get_json()
    assert stats["expense_count"] == 0
    assert stats["total_spend"] == 0
    assert stats["average_spend"] == 0


def test_profile_shows_average_and_top_category(alice_client):
    html = _html(alice_client.get("/profile"))
    text = _text(html)
    assert "Average spend" in text
    assert "₹31.03" in html  # 248.24 / 8
    assert "Top category" in text
    # Bills is 60.00 of 248.24 ≈ 24.2%
    assert "Bills" in text
    assert "24.2" in html


def test_top_category_is_highest_aggregate_spend(alice_client):
    """Bills 60.00 beats Shopping 55.00; Food's two rows only sum to 31.25."""
    html = _html(alice_client.get("/profile"))
    text = _text(html)
    top_at = text.index("Top category")
    window = text[top_at:top_at + 120]
    assert "Bills" in window
    assert "Shopping" not in window
    assert "Food" not in window


def test_breakdown_includes_share_pct_summing_to_100(alice_client):
    breakdown = alice_client.get("/api/profile/breakdown").get_json()["breakdown"]
    assert "share_pct" in breakdown[0]
    assert sum(row["share_pct"] for row in breakdown) == pytest.approx(100.0, abs=0.5)
    shopping = next(r for r in breakdown if r["category"] == "Shopping")
    assert shopping["share_pct"] == pytest.approx(22.2, abs=0.1)


def test_empty_account_renders_zero_money_and_dashes(empty_client):
    html = _html(empty_client.get("/profile"))
    text = _text(html)
    assert "No expenses yet" in text
    assert "₹0.00" in html
    assert "No spending data for this period." in text
    assert "Top category" in text


def test_filtered_empty_never_prints_zero_money(alice_client):
    html = _html(
        alice_client.get(
            "/profile?category=Food&date_from=2026-09-05&date_to=2026-09-05"
        )
    )
    assert "₹0.00" not in html
    assert "0.00" not in html
    assert "No expenses match these filters" in html


# ------------------------------------------------------------------ #
# Currency + chart formatting                                        #
# ------------------------------------------------------------------ #

def test_money_uses_indian_grouping_for_thousands(clean, client):
    uid = _insert_user(clean, "Rich", "rich@example.com")
    _insert_expense(clean, uid, 11602.70, "Shopping", "2026-09-20", "Big buy")
    _login(client, "rich@example.com")
    html = _html(client.get("/profile"))
    assert "₹11,602.70" in html
    assert "₹11602.70" not in html


def test_donut_uses_css_conic_gradient_not_an_external_library(alice_client):
    html = _html(alice_client.get("/profile"))
    assert "conic-gradient(" in html
    # No chart CDN / canvas library sneaked in for one donut.
    assert "chart.js" not in html.lower()
    assert "d3.js" not in html.lower()
    assert "<canvas" not in html.lower()


def test_category_rows_carry_amount_and_share(alice_client):
    html = _html(alice_client.get("/profile"))
    text = _text(html)
    for amount in ("₹60.00", "₹45.00", "₹55.00", "₹31.25"):
        assert amount in html
    assert re.search(r"Shopping .*55\.00 .*22\.2", text)


# ------------------------------------------------------------------ #
# App shell / navigation                                             #
# ------------------------------------------------------------------ #

def test_profile_renders_dashboard_shell(alice_client):
    html = _html(alice_client.get("/profile"))
    assert 'class="app-header"' in html
    assert 'class="app-sidebar"' in html
    assert "Your profile" in html
    assert "Track every rupee with clarity." in html
    assert "Filter your transactions" in html
    assert "Account settings" in html
    assert "app-footer" in html


def test_sidebar_marks_profile_active_and_links_analytics(alice_client):
    html = _html(alice_client.get("/profile"))
    active = re.findall(r'<a[^>]*class="side-link is-active"[^>]*>.*?</a>', html, re.DOTALL)
    assert any("Profile" in block for block in active)
    assert "Analytics" in html
    assert 'href="/analytics"' in html
    assert "is-disabled" not in html
    assert re.search(r"soon", html, re.IGNORECASE)


def test_sidebar_transactions_and_settings_point_at_real_routes(alice_client):
    html = _html(alice_client.get("/profile"))
    assert "/profile/history" in html
    assert "/profile/edit" in html
    assert "/profile/password" in html


def test_edit_profile_action_is_a_real_route(alice_client):
    resp = alice_client.get("/profile/edit")
    assert resp.status_code == 200
    html = _html(alice_client.get("/profile"))
    assert 'href="/profile/edit"' in html


def test_history_page_shares_the_shell(alice_client):
    html = _html(alice_client.get("/profile/history"))
    assert 'class="app-sidebar"' in html
    assert "Transactions" in html


# ------------------------------------------------------------------ #
# Safety contracts the redesign must not weaken                       #
# ------------------------------------------------------------------ #

def test_delete_account_rejects_get(alice_client):
    resp = alice_client.get("/profile/delete")
    assert resp.status_code == 405


def test_delete_account_is_post_and_uses_session_user(client, clean, db_conn):
    mine = _insert_user(clean, "Me", "me@example.com")
    other = _insert_user(clean, "Other", "other@example.com")
    _insert_expense(clean, other, 99.99, "Food", "2026-09-02", "Not yours")

    _login(client, "me@example.com")
    resp = client.post("/profile/delete", follow_redirects=False)
    assert resp.status_code == 302
    assert urlparse(resp.headers["Location"]).path == "/"

    gone = db_conn.execute(
        "SELECT 1 FROM users WHERE id = ?", (mine,)
    ).fetchone()
    assert gone is None
    survivor = db_conn.execute(
        "SELECT 1 FROM users WHERE id = ?", (other,)
    ).fetchone()
    assert survivor is not None
    assert db_conn.execute(
        "SELECT COUNT(*) FROM expenses WHERE user_id = ?", (other,)
    ).fetchone()[0] == 1


def test_user_cannot_see_another_users_dashboard(db_conn, alice, alice_client):
    bob = _insert_user(db_conn, "Bob", "bob@example.com")
    _insert_expense(db_conn, bob, 12345.67, "Food", "2026-09-10", "Bob secret")

    html = _html(alice_client.get("/profile"))
    assert "Bob secret" not in html
    assert "12,345.67" not in html
    assert "12345.67" not in html

    stats = alice_client.get("/api/profile/stats").get_json()
    assert stats["expense_count"] == COUNT_ALL
    assert stats["total_spend"] == pytest.approx(TOTAL_ALL)


def test_description_html_is_escaped_on_dashboard(clean, client):
    uid = _insert_user(clean, "Eve", "eve@example.com")
    _insert_expense(
        clean, uid, 1.0, "Other", "2026-09-20", "<script>alert(1)</script>"
    )
    _login(client, "eve@example.com")
    html = _html(client.get("/profile"))
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;" in html


def test_inline_chart_style_has_no_user_text(db_conn, alice, alice_client):
    """Donut gradient is built from colour constants + numbers only."""
    _insert_expense(
        db_conn, alice, 5.0, '"><img src=x onerror=alert(1)>', "2026-09-29", "inject"
    )
    html = _html(alice_client.get("/profile"))
    gradient_styles = re.findall(r'conic-gradient\([^"]+\)', html)
    assert gradient_styles
    for style in gradient_styles:
        assert "alert" not in style
        assert "onerror" not in style
        assert "<" not in style


def test_password_hash_never_renders_on_dashboard(alice_client):
    html = _html(alice_client.get("/profile"))
    assert "password" not in html.lower() or "Change password" in html
    assert "pbkdf2" not in html.lower()
    assert "scrypt" not in html.lower()


def test_registration_login_still_work_after_redesign(client, clean):
    resp = client.post(
        "/register",
        data={"name": "New", "email": "new@example.com", "password": "password123"},
        follow_redirects=False,
    )
    assert resp.status_code == 302
    assert urlparse(resp.headers["Location"]).path == "/login"

    _login(client, "new@example.com")
    home = client.get("/profile")
    assert home.status_code == 200
    assert "New" in _html(home)

    out = client.get("/logout", follow_redirects=False)
    assert out.status_code == 302
    assert urlparse(out.headers["Location"]).path == "/"
