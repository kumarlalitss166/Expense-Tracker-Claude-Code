"""Tests for Step 07 — Forgot Password.

Source of truth: .claude/specs/07-forgot-password.md

These tests exercise the public /forgot-password flow and the /login?reset=1
success banner through the real Flask app and the isolated temp database wired
up by the repository-root conftest.py. They never touch the real
expense_tracker.db. Seed users/rows are wiped per test by the `clean` fixture
so every assertion runs against data the test itself created.
"""

import re
from urllib.parse import parse_qs, urlparse

import pytest
from werkzeug.security import check_password_hash, generate_password_hash


# ------------------------------------------------------------------ #
# Spec constants — exact strings from 07-forgot-password.md          #
# ------------------------------------------------------------------ #

OLD_PASSWORD = "oldpassword123"
NEW_PASSWORD = "brandnew45678"

SUCCESS_BANNER = "Your password has been reset. Sign in with your new password."
SECURITY_HINT = (
    "Learning project: no email check "
    "— anyone who knows your email can reset this password."
)

ERR_EMPTY = "Please fill in all fields."
ERR_BAD_EMAIL = "Please enter a valid email address."
ERR_SHORT = "Password must be at least 8 characters."
ERR_MISMATCH = "New passwords do not match."
ERR_UNKNOWN = "No account found with that email address."
ERR_LOGIN = "Invalid email or password."


# ------------------------------------------------------------------ #
# Helpers                                                            #
# ------------------------------------------------------------------ #

def _insert_user(conn, name, email, password=OLD_PASSWORD):
    cur = conn.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
        (name, email, generate_password_hash(password)),
    )
    conn.commit()
    return cur.lastrowid


def _login(client, email, password=OLD_PASSWORD):
    return client.post(
        "/login",
        data={"email": email, "password": password},
        follow_redirects=False,
    )


def _html(resp):
    return resp.get_data(as_text=True)


def _reset(client, email, new_password, confirm_password=None):
    """POST /forgot-password; confirm defaults to matching new_password."""
    if confirm_password is None:
        confirm_password = new_password
    return client.post(
        "/forgot-password",
        data={
            "email": email,
            "new_password": new_password,
            "confirm_password": confirm_password,
        },
        follow_redirects=False,
    )


def _assert_validation_error(resp, message):
    """Validation failures: HTTP 400, re-rendered page carrying the exact string."""
    assert resp.status_code == 400, f"expected 400, got {resp.status_code}"
    assert message in _html(resp), f"expected error {message!r} in response HTML"


def _link_hrefs(html, text):
    """hrefs of <a> tags whose visible label is exactly `text`."""
    hrefs = []
    for tag in re.findall(r"<a\b[^>]*>.*?</a>", html, re.DOTALL):
        label = re.sub(r"<[^>]+>", "", tag).strip()
        if label == text:
            m = re.search(r'href="([^"]*)"', tag)
            if m:
                hrefs.append(m.group(1))
    return hrefs


def _user_by_email(conn, email):
    return conn.execute(
        "SELECT id, name, email, password_hash FROM users WHERE email = ?",
        (email,),
    ).fetchone()


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
def user(clean):
    """A single account (Alice) with the usual old password. Returns her id."""
    return _insert_user(clean, "Alice", "alice@example.com", OLD_PASSWORD)


# ------------------------------------------------------------------ #
# Page affordances                                                   #
# ------------------------------------------------------------------ #

def test_login_page_shows_forgot_password_link_to_reset_form(client, user):
    """DoD: sign-in page shows a 'Forgot password?' link opening /forgot-password."""
    resp = client.get("/login")
    assert resp.status_code == 200
    hrefs = _link_hrefs(_html(resp), "Forgot password?")
    assert hrefs, "login page must show a 'Forgot password?' link"
    assert any(urlparse(h).path == "/forgot-password" for h in hrefs), hrefs


def test_forgot_password_form_fields_and_back_to_sign_in_link(client, user):
    """DoD: GET /forgot-password renders email + new_password + confirm_password
    fields and a link back to sign-in."""
    resp = client.get("/forgot-password")
    assert resp.status_code == 200
    html = _html(resp)

    for field in ("email", "new_password", "confirm_password"):
        assert f'name="{field}"' in html, f"missing form field {field!r}"

    hrefs = _link_hrefs(html, "Sign in")
    assert hrefs, "reset page must link back to sign-in"
    assert any(urlparse(h).path == "/login" for h in hrefs), hrefs


def test_reset_page_shows_learning_project_security_hint(client, user):
    """DoD: the reset page shows the learning-project security hint."""
    resp = client.get("/forgot-password")
    assert resp.status_code == 200
    assert SECURITY_HINT in _html(resp)


def test_forgot_password_get_redirects_to_profile_when_signed_in(client, user):
    """DoD: GET /forgot-password while signed in redirects to /profile."""
    _login(client, "alice@example.com", OLD_PASSWORD)
    resp = client.get("/forgot-password", follow_redirects=False)
    assert resp.status_code == 302
    assert urlparse(resp.headers["Location"]).path == "/profile"


# ------------------------------------------------------------------ #
# Happy path: reset, redirect, sign-in with the new password          #
# ------------------------------------------------------------------ #

def test_valid_reset_redirects_to_login_with_reset_flag(client, user):
    """DoD: valid POST → 302 to /login with reset=1 in the query string."""
    resp = _reset(client, "alice@example.com", NEW_PASSWORD)
    assert resp.status_code == 302
    loc = urlparse(resp.headers["Location"])
    assert loc.path == "/login"
    assert parse_qs(loc.query).get("reset") == ["1"]


def test_password_hash_updated_in_db_and_not_plaintext(client, clean, user):
    """DoD: reset writes a real werkzeug password_hash — changed, never plaintext."""
    before = _user_by_email(clean, "alice@example.com")["password_hash"]

    resp = _reset(client, "alice@example.com", NEW_PASSWORD)
    assert resp.status_code == 302

    row = _user_by_email(clean, "alice@example.com")
    assert row["password_hash"] != before, "password_hash must change on reset"
    assert row["password_hash"] != NEW_PASSWORD, "must never store plaintext"
    assert NEW_PASSWORD not in row["password_hash"], "plaintext leaked into hash"
    assert check_password_hash(row["password_hash"], NEW_PASSWORD)
    assert not check_password_hash(row["password_hash"], OLD_PASSWORD)


def test_login_succeeds_with_new_password_after_reset(client, clean, user):
    """DoD: after a successful reset the user can sign in with the new password."""
    assert _reset(client, "alice@example.com", NEW_PASSWORD).status_code == 302

    resp = _login(client, "alice@example.com", NEW_PASSWORD)
    assert resp.status_code == 302
    assert urlparse(resp.headers["Location"]).path == "/profile"


def test_old_password_rejected_after_reset(client, clean, user):
    """DoD: after reset the old password is rejected (400, 'Invalid email or password.')."""
    assert _reset(client, "alice@example.com", NEW_PASSWORD).status_code == 302

    resp = _login(client, "alice@example.com", OLD_PASSWORD)
    _assert_validation_error(resp, ERR_LOGIN)


def test_user_not_signed_in_after_reset(client, clean, user):
    """DoD: reset does not auto-login — /profile still redirects to /login."""
    assert _reset(client, "alice@example.com", NEW_PASSWORD).status_code == 302

    resp = client.get("/profile", follow_redirects=False)
    assert resp.status_code == 302
    assert urlparse(resp.headers["Location"]).path == "/login"


# ------------------------------------------------------------------ #
# Success banner on /login                                           #
# ------------------------------------------------------------------ #

def test_login_reset_flag_shows_success_banner(client, user):
    """DoD: /login?reset=1 shows the exact success banner text."""
    resp = client.get("/login?reset=1")
    assert resp.status_code == 200
    assert SUCCESS_BANNER in _html(resp)


def test_login_banner_only_for_reset_value_exactly_one(client, user):
    """Spec rule: only reset == "1" shows the banner — other values must not."""
    for query in ("", "?reset=0", "?reset=yes", "?reset=11"):
        html = _html(client.get(f"/login{query}"))
        assert SUCCESS_BANNER not in html, f"banner must not appear for /login{query}"


# ------------------------------------------------------------------ #
# Validation errors — exact status + exact strings from the spec      #
# ------------------------------------------------------------------ #

@pytest.mark.parametrize(
    "data",
    [
        {"email": "", "new_password": "", "confirm_password": ""},
        {"email": "", "new_password": NEW_PASSWORD, "confirm_password": NEW_PASSWORD},
        {"email": "alice@example.com", "new_password": "", "confirm_password": NEW_PASSWORD},
        {"email": "alice@example.com", "new_password": NEW_PASSWORD, "confirm_password": ""},
    ],
    ids=["all-empty", "email-empty", "new-empty", "confirm-empty"],
)
def test_empty_fields_return_fill_in_all_fields(client, user, data):
    """DoD: any empty field → 400 'Please fill in all fields.'"""
    resp = client.post("/forgot-password", data=data, follow_redirects=False)
    _assert_validation_error(resp, ERR_EMPTY)


def test_invalid_email_returns_valid_email_error(client, user):
    """DoD: malformed email → 400 'Please enter a valid email address.'"""
    resp = _reset(client, "not-an-email", NEW_PASSWORD)
    _assert_validation_error(resp, ERR_BAD_EMAIL)


def test_short_password_returns_min_length_error(client, user):
    """DoD: password shorter than 8 characters → 400 'Password must be at least 8 characters.'"""
    resp = _reset(client, "alice@example.com", "short12", "short12")
    _assert_validation_error(resp, ERR_SHORT)


def test_password_exactly_eight_characters_is_accepted(client, clean, user):
    """Boundary of 'at least 8 characters': an 8-char password succeeds."""
    eight = "abcd1234"
    assert len(eight) == 8
    resp = _reset(client, "alice@example.com", eight)
    assert resp.status_code == 302
    row = _user_by_email(clean, "alice@example.com")
    assert check_password_hash(row["password_hash"], eight)


def test_mismatched_passwords_return_mismatch_error(client, user):
    """DoD: mismatched new/confirm → 400 'New passwords do not match.'"""
    resp = _reset(client, "alice@example.com", NEW_PASSWORD, "different9999")
    _assert_validation_error(resp, ERR_MISMATCH)


def test_unknown_email_returns_no_account_error(client, user):
    """DoD: an email with no account → 400 'No account found with that email address.'"""
    resp = _reset(client, "nobody@example.com", NEW_PASSWORD)
    _assert_validation_error(resp, ERR_UNKNOWN)


# ------------------------------------------------------------------ #
# Validation order (spec rule: 1 empty → 2 email → 3 length → 4 match) #
# ------------------------------------------------------------------ #

def test_validation_order_empty_beats_invalid_email(client, user):
    """Empty fields win over a malformed email (rule 1 before rule 2)."""
    resp = client.post(
        "/forgot-password",
        data={"email": "", "new_password": "x", "confirm_password": "y"},
        follow_redirects=False,
    )
    _assert_validation_error(resp, ERR_EMPTY)


def test_validation_order_email_beats_password_rules(client, user):
    """Malformed email wins over short password (rule 2 before rule 3)."""
    resp = _reset(client, "not-an-email", "x", "y")
    _assert_validation_error(resp, ERR_BAD_EMAIL)


def test_validation_order_length_beats_mismatch(client, user):
    """Short password wins over mismatch (rule 3 before rule 4)."""
    resp = _reset(client, "alice@example.com", "x", "y")
    _assert_validation_error(resp, ERR_SHORT)


# ------------------------------------------------------------------ #
# Email matching + password handling rules                           #
# ------------------------------------------------------------------ #

def test_email_matching_is_case_insensitive(client, clean, user):
    """DoD: email matching is case-insensitive; input is stripped + lowercased."""
    resp = _reset(client, "  ALICE@Example.COM  ", NEW_PASSWORD)
    assert resp.status_code == 302

    row = _user_by_email(clean, "alice@example.com")
    assert row is not None, "stored lowercase email must still resolve"
    assert check_password_hash(row["password_hash"], NEW_PASSWORD)


def test_passwords_are_not_stripped(client, clean, user):
    """Spec rule: strip+lowercase email only — never strip passwords.
    '  abcde  ' is 9 characters (>= 8); stripping would shrink it below the
    minimum and the reset would fail."""
    padded = "  abcde  "
    assert len(padded) >= 8 and len(padded.strip()) < 8

    resp = _reset(client, "alice@example.com", padded)
    assert resp.status_code == 302
    row = _user_by_email(clean, "alice@example.com")
    assert check_password_hash(row["password_hash"], padded)
    assert not check_password_hash(row["password_hash"], padded.strip())


# ------------------------------------------------------------------ #
# Invariants implied by the feature: failed input persists nothing,   #
# only password_hash changes, other accounts untouched                #
# ------------------------------------------------------------------ #

def test_failed_reset_does_not_change_password_hash(client, clean, user):
    """Invalid input must not be persisted — the stored hash stays the old one."""
    before = _user_by_email(clean, "alice@example.com")["password_hash"]

    for resp in (
        _reset(client, "alice@example.com", "x", "x"),          # too short
        _reset(client, "alice@example.com", NEW_PASSWORD, "y"),  # mismatch
        _reset(client, "nobody@example.com", NEW_PASSWORD),      # unknown email
        _reset(client, "not-an-email", NEW_PASSWORD),            # bad email
    ):
        assert resp.status_code == 400

    after = _user_by_email(clean, "alice@example.com")["password_hash"]
    assert after == before
    assert check_password_hash(after, OLD_PASSWORD)


def test_reset_updates_only_password_hash(client, clean, user):
    """Spec rule: UPDATE writes password_hash only — never name or email."""
    original = _user_by_email(clean, "alice@example.com")

    resp = _reset(client, "alice@example.com", NEW_PASSWORD)
    assert resp.status_code == 302

    row = _user_by_email(clean, "alice@example.com")
    assert row["name"] == original["name"]
    assert row["email"] == original["email"]
    assert row["id"] == original["id"]
    assert row["password_hash"] != original["password_hash"]


def test_reset_leaves_other_accounts_untouched(client, clean):
    """A reset for one account must not change any other account's password."""
    alice_id = _insert_user(clean, "Alice", "alice@example.com", OLD_PASSWORD)
    bob_id = _insert_user(clean, "Bob", "bob@example.com", OLD_PASSWORD)
    bob_before = _user_by_email(clean, "bob@example.com")["password_hash"]

    resp = _reset(client, "alice@example.com", NEW_PASSWORD)
    assert resp.status_code == 302

    assert _user_by_email(clean, "bob@example.com")["password_hash"] == bob_before
    assert check_password_hash(bob_before, OLD_PASSWORD)
    # Sanity: Alice did change.
    alice_after = _user_by_email(clean, "alice@example.com")["password_hash"]
    assert check_password_hash(alice_after, NEW_PASSWORD)
    assert alice_id != bob_id
