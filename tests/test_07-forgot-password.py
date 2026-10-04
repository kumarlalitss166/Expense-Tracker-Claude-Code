"""Tests for the forgot-password flow (no OTP / email verification).

Learning-project scope: /forgot-password accepts email + new password +
confirm password and updates the account immediately. Success redirects to
/login (no auto-login). These tests use the isolated temp database wired up
by the repository-root conftest.py and never touch expense_tracker.db.
"""

from urllib.parse import urlparse

import pytest
from werkzeug.security import check_password_hash, generate_password_hash


PASSWORD = "password123"
NEW_PASSWORD = "newpass123"


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
    return client.post(
        "/login", data={"email": email, "password": password}, follow_redirects=False
    )


def _html(resp):
    return resp.get_data(as_text=True)


def _reset(client, email, new=NEW_PASSWORD, confirm=None, status_code=None):
    resp = client.post(
        "/forgot-password",
        data={
            "email": email,
            "new_password": new,
            "confirm_password": NEW_PASSWORD if confirm is None else confirm,
        },
        follow_redirects=False,
    )
    if status_code is not None:
        assert resp.status_code == status_code, _html(resp)[:300]
    return resp


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
    return _insert_user(clean, "Alice", "alice@example.com")


# ------------------------------------------------------------------ #
# Page / link                                                        #
# ------------------------------------------------------------------ #

def test_forgot_password_page_renders_form(client):
    resp = client.get("/forgot-password")
    assert resp.status_code == 200
    html = _html(resp)
    assert 'name="email"' in html
    assert 'name="new_password"' in html
    assert 'name="confirm_password"' in html
    assert "Reset password" in html


def test_login_page_links_to_forgot_password(client):
    html = _html(client.get("/login"))
    assert "/forgot-password" in html
    assert "Forgot password?" in html


def test_login_page_shows_success_message(client):
    resp = client.get("/login?reset=1")
    assert resp.status_code == 200
    assert (
        "Your password has been reset. Sign in with your new password."
        in _html(resp)
    )


def test_page_shows_security_hint(client):
    html = _html(client.get("/forgot-password"))
    assert "Learning project" in html
    assert "reset this password" in html


def test_signed_in_user_is_redirected_away(client, alice):
    _login(client, "alice@example.com")
    resp = client.get("/forgot-password")
    assert resp.status_code == 302
    assert urlparse(resp.headers["Location"]).path == "/profile"


# ------------------------------------------------------------------ #
# Validation errors                                                  #
# ------------------------------------------------------------------ #

def test_missing_fields_error(client, alice):
    resp = client.post("/forgot-password", data={}, follow_redirects=False)
    assert resp.status_code == 400
    assert "Please fill in all fields." in _html(resp)


def test_invalid_email_error(client, alice):
    resp = _reset(client, "not-an-email", status_code=400)
    assert "Please enter a valid email address." in _html(resp)


def test_short_password_error(client, alice):
    resp = _reset(client, "alice@example.com", new="short", confirm="short", status_code=400)
    assert "Password must be at least 8 characters." in _html(resp)


def test_password_mismatch_error(client, alice):
    resp = _reset(client, "alice@example.com", new=NEW_PASSWORD, confirm="other12345", status_code=400)
    assert "New passwords do not match." in _html(resp)


def test_unknown_email_error(client, alice):
    resp = _reset(client, "ghost@example.com", status_code=400)
    assert "No account found with that email address." in _html(resp)


# ------------------------------------------------------------------ #
# Successful reset                                                   #
# ------------------------------------------------------------------ #

def test_successful_reset_redirects_to_login(client, alice):
    resp = _reset(client, "alice@example.com", status_code=302)
    location = urlparse(resp.headers["Location"])
    assert location.path == "/login"
    assert "reset=1" in location.query


def test_successful_reset_updates_password(client, alice, db_conn):
    _reset(client, "alice@example.com", status_code=302)

    row = db_conn.execute(
        "SELECT password_hash FROM users WHERE email = ?", ("alice@example.com",)
    ).fetchone()
    assert row is not None
    assert check_password_hash(row["password_hash"], NEW_PASSWORD)

    login = _login(client, "alice@example.com", NEW_PASSWORD)
    assert login.status_code == 302
    assert urlparse(login.headers["Location"]).path == "/profile"


def test_old_password_no_longer_works(client, alice):
    _reset(client, "alice@example.com", status_code=302)
    login = _login(client, "alice@example.com", PASSWORD)
    assert login.status_code == 400
    assert "Invalid email or password." in _html(login)


def test_no_auto_login_after_reset(client, alice):
    _reset(client, "alice@example.com", status_code=302)
    resp = client.get("/profile")
    assert resp.status_code == 302
    assert urlparse(resp.headers["Location"]).path == "/login"


def test_email_matching_is_case_insensitive(client, alice, db_conn):
    resp = _reset(client, "  Alice@Example.COM  ", status_code=302)
    assert urlparse(resp.headers["Location"]).path == "/login"

    row = db_conn.execute(
        "SELECT password_hash FROM users WHERE email = ?", ("alice@example.com",)
    ).fetchone()
    assert check_password_hash(row["password_hash"], NEW_PASSWORD)
