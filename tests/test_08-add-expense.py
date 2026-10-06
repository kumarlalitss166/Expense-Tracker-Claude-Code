"""Tests for the Add Expense coming-soon module (spec: .claude/specs/08-add-expense.md).

Step 08 ships a signed-in coming-soon placeholder for /expenses/add — NOT a
create form. These tests cover the spec's Definition of done plus the explicit
template contracts (h1 id / aria-labelledby, 24x24 icon, shared coming-soon-*
structure) and the safety rules (no POST handler, no form fields, no INSERT,
edit/delete stubs frozen, /analytics untouched).

Copy strings are taken verbatim from the spec (em dashes are U+2014 with a
space on each side). The edit/delete stub strings are the frozen "still
return their stub strings" baseline the DoD pins for this step.
"""

import re
from pathlib import Path

import pytest
from flask import render_template
from werkzeug.security import generate_password_hash


PASSWORD = "password123"

# Exact copy from .claude/specs/08-add-expense.md (U+2014 em dashes).
DASH = "—"  # em dash U+2014, spaces around per spec
BADGE = "Coming Soon"
TITLE = "Add Expense"
BODY = (
    "We're building a simple way to log every rupee you spend "
    f"{DASH} amount, category, date, and a note "
    f"{DASH} so your dashboard stays up to date."
)
FOOT = "We're crafting something special"

# Frozen stub baselines ("still return their stub strings").
EDIT_STUB = f"Edit expense {DASH} coming in Step 8"
DELETE_STUB = f"Delete expense {DASH} coming in Step 9"

STYLE_CSS = Path(__file__).resolve().parent.parent / "static" / "css" / "style.css"

# Shared coming-soon structure the spec says expense_add.html must reuse
# (blobs, card, corner accents, icon wrap + glow, badge, title, copy,
# progress dots + foot, line).
COMING_SOON_CLASSES = [
    "coming-soon-blob",
    "coming-soon-card",
    "coming-soon-accent",
    "coming-soon-icon-wrap",
    "coming-soon-icon-glow",
    "coming-soon-icon",
    "coming-soon-badge",
    "coming-soon-title",
    "coming-soon-copy",
    "coming-soon-dots",
    "coming-soon-foot",
    "coming-soon-line",
]


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


def _insert_expense(conn, user_id, amount, category, date, description=""):
    cur = conn.execute(
        "INSERT INTO expenses (user_id, amount, category, date, description) "
        "VALUES (?, ?, ?, ?, ?)",
        (user_id, amount, category, date, description),
    )
    conn.commit()
    return cur.lastrowid


def _login(client, email, password=PASSWORD):
    resp = client.post(
        "/login", data={"email": email, "password": password}, follow_redirects=False
    )
    assert resp.status_code == 302
    return resp


def _html(resp):
    return resp.get_data(as_text=True)


def _visible(html):
    """Collapse whitespace the way a browser renders text nodes."""
    return " ".join(html.split())


@pytest.fixture()
def clean(db_conn):
    db_conn.execute("DELETE FROM expenses")
    db_conn.execute("DELETE FROM users")
    db_conn.commit()
    return db_conn


@pytest.fixture()
def alice(clean):
    return _insert_user(clean, "Alice", "alice@example.com")


@pytest.fixture()
def alice_client(client, alice):
    _login(client, "alice@example.com")
    return client


# ------------------------------------------------------------------ #
# Auth gate                                                          #
# ------------------------------------------------------------------ #

def test_add_expense_redirects_anonymous_to_login(client, clean):
    """DoD: signed-out GET /expenses/add redirects to /login (302)."""
    resp = client.get("/expenses/add", follow_redirects=False)
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]


# ------------------------------------------------------------------ #
# Page rendering                                                     #
# ------------------------------------------------------------------ #

def test_add_expense_renders_coming_soon_card_with_title(alice_client):
    """DoD: signed-in GET returns 200 and renders the coming-soon card titled 'Add Expense'."""
    resp = alice_client.get("/expenses/add")
    assert resp.status_code == 200
    html = _html(resp)
    assert TITLE in html
    assert "coming-soon-card" in html


def test_add_expense_shows_badge_body_copy_and_pulsing_dots(alice_client):
    """DoD: the page shows the 'Coming Soon' badge, the body copy, and the pulsing dots row."""
    html = _html(alice_client.get("/expenses/add"))
    assert BADGE in html
    assert BODY in _visible(html)  # exact spec copy, U+2014 em dashes with spaces
    assert FOOT in html
    assert "coming-soon-dots" in html


def test_add_expense_page_body_uses_add_expense_body_class(alice_client):
    """DoD: the page body uses add-expense-body."""
    html = _html(alice_client.get("/expenses/add"))
    assert re.search(r'<body[^>]*class="[^"]*add-expense-body', html)


def test_add_expense_card_reuses_shared_coming_soon_classes(alice_client):
    """Template contract: the exact coming-soon-* structure is reused (no parallel card)."""
    html = _html(alice_client.get("/expenses/add"))
    for cls in COMING_SOON_CLASSES:
        assert cls in html, f"expected shared class {cls!r} on the coming-soon card"


def test_add_expense_heading_id_and_aria_labelledby(alice_client):
    """Template contract: <h1> id is add-expense-title and the section aria-labelledby points at it."""
    html = _html(alice_client.get("/expenses/add"))
    assert re.search(r'<h1[^>]*id="add-expense-title"', html)
    assert re.search(r'<section[^>]*aria-labelledby="add-expense-title"', html)


def test_add_expense_icon_svg_uses_24_viewbox_and_round_linecap(alice_client):
    """Template contract: icon SVG keeps the 24x24 viewBox and stroke-linecap='round' style."""
    html = _html(alice_client.get("/expenses/add"))
    assert 'viewBox="0 0 24 24"' in html
    assert 'stroke-linecap="round"' in html


# ------------------------------------------------------------------ #
# Static CSS (DoD: no duplicated card CSS)                           #
# ------------------------------------------------------------------ #

def test_style_css_extends_page_chrome_selectors_to_add_expense_body():
    """Files-to-change contract: .add-expense-body joins the .analytics-body page-chrome selectors."""
    css = STYLE_CSS.read_text(encoding="utf-8")
    assert re.search(r"\.analytics-body\s*,\s*\.add-expense-body", css)


def test_style_css_has_no_parallel_add_expense_card_system():
    """DoD/rules: shared coming-soon-* classes are reused as-is — no duplicated card CSS."""
    css = STYLE_CSS.read_text(encoding="utf-8")
    assert "add-expense-card" not in css
    assert ".add-expense-body .coming-soon-card" not in css


# ------------------------------------------------------------------ #
# Marketing navbar                                                   #
# ------------------------------------------------------------------ #

def test_navbar_hides_add_expense_from_anonymous(client, clean):
    """Navbar entry lives in the signed-in block — hidden while signed out."""
    html = _html(client.get("/"))
    assert 'href="/expenses/add"' not in html
    assert "Add expense" not in html


def test_navbar_shows_add_expense_when_logged_in(alice_client):
    """Navbar shows the 'Add expense' link for a signed-in user."""
    html = _html(alice_client.get("/"))
    assert 'href="/expenses/add"' in html
    assert "Add expense" in html


def test_navbar_marks_add_expense_active_on_page(alice_client):
    """DoD: the signed-in navbar 'Add expense' link is is-active on this page."""
    html = _html(alice_client.get("/expenses/add"))
    active = re.findall(
        r'<a[^>]*class="[^"]*is-active[^"]*"[^>]*>\s*Add expense\s*</a>',
        html,
        re.DOTALL,
    )
    assert active, "expected Add expense nav link to carry is-active"


def test_navbar_does_not_mark_profile_active_on_add_expense(alice_client):
    """Active state is endpoint-specific: Profile is not active on the add-expense page."""
    html = _html(alice_client.get("/expenses/add"))
    assert not re.search(
        r'<a[^>]*class="[^"]*is-active[^"]*"[^>]*>\s*Profile\s*</a>',
        html,
        re.DOTALL,
    )


# ------------------------------------------------------------------ #
# App sidebar                                                        #
# ------------------------------------------------------------------ #

def test_sidebar_shows_add_expense_link_after_history_with_soon_tag(alice_client):
    """Sidebar gets an 'Add expense' row after History, with the SOON side-tag."""
    html = _html(alice_client.get("/profile"))
    assert 'href="/expenses/add"' in html
    assert (
        html.find('href="/profile/history"') < html.find('href="/expenses/add"')
    ), "Add expense row must come after the History row"
    link = re.search(r'<a[^>]*href="/expenses/add"[^>]*>(.*?)</a>', html, re.DOTALL)
    assert link, "expected a sidebar anchor to /expenses/add"
    assert re.search(r"<span>\s*Add expense\s*</span>", link.group(1))
    assert "SOON" in link.group(1), "expected the side-tag SOON on the Add expense row"


def test_sidebar_marks_add_expense_active_only_on_add_expense_endpoint(app, clean):
    """Sidebar contract: active when request.endpoint == 'add_expense'.

    /expenses/add renders through base.html, so the sidebar is not part of that
    response; the partial is rendered under a request context for the route so
    its active-state contract can be observed.
    """
    active_re = re.compile(
        r'<a[^>]*class="[^"]*is-active[^"]*"[^>]*>.*?<span>\s*Add expense\s*</span>',
        re.DOTALL,
    )

    with app.test_request_context("/expenses/add"):
        on_page = render_template("partials/app_sidebar.html")
    assert active_re.search(on_page), (
        "expected sidebar Add expense link to carry is-active on /expenses/add"
    )

    with app.test_request_context("/profile"):
        off_page = render_template("partials/app_sidebar.html")
    assert not active_re.search(off_page), (
        "sidebar Add expense link must not be is-active outside the add-expense route"
    )


# ------------------------------------------------------------------ #
# Safety contracts (DoD + rules: no form, no POST, no writes)        #
# ------------------------------------------------------------------ #

def test_post_add_expense_returns_405(alice_client):
    """DoD: POST /expenses/add still returns 405 (no POST handler added)."""
    resp = alice_client.post("/expenses/add")
    assert resp.status_code == 405


def test_add_expense_renders_no_form_fields(alice_client):
    """Rules: no form fields collected on this placeholder page."""
    html = _html(alice_client.get("/expenses/add"))
    assert "<form" not in html
    assert "<input" not in html
    assert "<select" not in html
    assert "<textarea" not in html


def test_add_expense_does_not_write_expenses(alice_client, alice, clean):
    """Rules: the route is a pure render — no expense is written or modified."""
    _insert_expense(clean, alice, 99.5, "Food", "2026-01-05", "before")
    rows_before = [
        tuple(r)
        for r in clean.execute(
            "SELECT id, user_id, amount, category, date, description "
            "FROM expenses ORDER BY id"
        ).fetchall()
    ]
    resp = alice_client.get("/expenses/add")
    assert resp.status_code == 200
    rows_after = [
        tuple(r)
        for r in clean.execute(
            "SELECT id, user_id, amount, category, date, description "
            "FROM expenses ORDER BY id"
        ).fetchall()
    ]
    assert rows_after == rows_before


def test_edit_and_delete_stubs_unchanged(alice_client):
    """DoD: /expenses/<id>/edit and /expenses/<id>/delete still return their stub strings."""
    edit = alice_client.get("/expenses/1/edit")
    assert edit.status_code == 200
    assert _html(edit) == EDIT_STUB

    delete = alice_client.get("/expenses/1/delete")
    assert delete.status_code == 200
    assert _html(delete) == DELETE_STUB


def test_analytics_still_renders_unchanged(alice_client):
    """DoD: /analytics still renders unchanged."""
    resp = alice_client.get("/analytics")
    assert resp.status_code == 200
    html = _html(resp)
    assert "Advanced Analytics" in html
    assert BADGE in html
