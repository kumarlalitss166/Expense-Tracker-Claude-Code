"""Tests for the Analytics coming-soon module.

Covers the /analytics route (auth gate + template), the signed-in navbar
entry, and the active-state contract on both the marketing navbar and the
app sidebar.
"""

import re

import pytest
from werkzeug.security import generate_password_hash


PASSWORD = "password123"

# Exact copy from the Figma Coming Soon wireframe.
BADGE = "Coming soon"
TITLE = "Advanced Analytics"
BODY = "We're working on powerful insights and visualizations"
FOOT = "We're crafting something special"


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


def _login(client, email, password=PASSWORD):
    resp = client.post(
        "/login", data={"email": email, "password": password}, follow_redirects=False
    )
    assert resp.status_code == 302
    return resp


def _html(resp):
    return resp.get_data(as_text=True)


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

def test_analytics_redirects_anonymous_to_login(client, clean):
    resp = client.get("/analytics", follow_redirects=False)
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]


def test_analytics_renders_coming_soon_copy(alice_client):
    resp = alice_client.get("/analytics")
    assert resp.status_code == 200
    html = _html(resp)
    assert TITLE in html
    assert BADGE in html
    assert BODY in html
    assert FOOT in html
    assert "coming-soon-card" in html


# ------------------------------------------------------------------ #
# Navbar / active state                                              #
# ------------------------------------------------------------------ #

def test_omnibus_navbar_hides_analytics_from_anonymous(client, clean):
    html = _html(client.get("/"))
    assert 'href="/analytics"' not in html
    assert "Analytics" not in html


def test_omnibus_navbar_shows_analytics_when_logged_in(alice_client):
    html = _html(alice_client.get("/"))
    assert 'href="/analytics"' in html
    assert "Analytics" in html


def test_navbar_marks_analytics_active_on_page(alice_client):
    html = _html(alice_client.get("/analytics"))
    active = re.findall(
        r'<a[^>]*class="[^"]*is-active[^"]*"[^>]*>\s*Analytics\s*</a>',
        html,
        re.DOTALL,
    )
    assert active, "expected Analytics nav link to carry is-active"


def test_navbar_does_not_mark_profile_active_on_analytics(alice_client):
    html = _html(alice_client.get("/analytics"))
    assert not re.search(
        r'<a[^>]*class="[^"]*is-active[^"]*"[^>]*>\s*Profile\s*</a>',
        html,
        re.DOTALL,
    )


def test_sidebar_links_to_analytics_from_dashboard(alice_client):
    # /analytics renders through base.html (marketing shell), so the sidebar
    # is asserted from a dashboard page — Analytics must be a real link.
    html = _html(alice_client.get("/profile"))
    assert 'href="/analytics"' in html
    assert "is-disabled" not in html
    assert re.search(r"soon", html, re.IGNORECASE)
