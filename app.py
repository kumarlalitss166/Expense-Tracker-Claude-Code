import os
import re
import sqlite3
import time
from datetime import datetime
from functools import wraps
from urllib.parse import urlencode

from flask import Flask, g, jsonify, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from database.db import CATEGORIES, get_db, init_db, seed_db

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-me")


# ------------------------------------------------------------------ #
# Auth helpers                                                        #
# ------------------------------------------------------------------ #

def login_required(view):
    """Redirect to /login when nobody is signed in."""
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped


@app.context_processor
def inject_auth():
    return {"is_logged_in": "user_id" in session}


# ------------------------------------------------------------------ #
# Presentation helpers — formatting only, no business logic            #
# ------------------------------------------------------------------ #

# Sequential sage→deep-green ramp for the category donut (index-based,
# never derived from user input, so the style attribute stays safe).
DONUT_COLORS = (
    "#1a472a",
    "#2f6b45",
    "#4a8f63",
    "#6fae88",
    "#9bc7aa",
    "#c0dcc8",
    "#dcece2",
)

CATEGORY_BADGE_CLASS = {
    "Food": "cat-badge-food",
    "Transport": "cat-badge-transport",
    "Bills": "cat-badge-bills",
    "Health": "cat-badge-health",
    "Entertainment": "cat-badge-entertainment",
    "Shopping": "cat-badge-shopping",
    "Other": "cat-badge-other",
}


@app.template_filter("inr")
def format_inr(value):
    """Indian-rupee money string, e.g. 11602.7 -> '₹11,602.70'."""
    try:
        amount = float(value)
    except (TypeError, ValueError):
        amount = 0.0
    return f"₹{amount:,.2f}"


@app.template_filter("cat_badge")
def category_badge_class(category):
    """CSS class for a category chip; unknown names fall back safely."""
    return CATEGORY_BADGE_CLASS.get(category, "cat-badge-other")


def build_donut(breakdown):
    """Donut geometry for the category chart.

    -> None when there is nothing to draw, else
       {"gradient": str, "rows": list[dict], "total": float}
    where each row is a breakdown row plus a "color" key.
    The gradient string is built only from our colour constants and
    numbers, so it is safe to drop into a style attribute.
    """
    total = sum(row["total"] for row in breakdown)
    if total <= 0:
        return None

    stops = []
    rows = []
    acc = 0.0
    for index, row in enumerate(breakdown):
        color = DONUT_COLORS[index % len(DONUT_COLORS)]
        pct = row["total"] / total * 100.0
        start = acc
        acc += pct
        stops.append(f"{color} {start:.2f}% {acc:.2f}%")
        rows.append({**row, "color": color})

    return {
        "gradient": "conic-gradient(" + ", ".join(stops) + ")",
        "rows": rows,
        "total": total,
    }


# ------------------------------------------------------------------ #
# Validation helpers                                                  #
# ------------------------------------------------------------------ #

def is_valid_email(email):
    """True when *email* passes the same format rules enforced by /register."""
    local, sep, domain = email.partition("@")
    return not (
        email.count("@") != 1
        or not local
        or "." not in domain
        or domain.startswith(".")
        or domain.endswith(".")
        or ".." in domain
    )


ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _parse_iso_date(value):
    """Return *value* as an ISO date string, or None when absent/invalid."""
    if not value:
        return None
    if not ISO_DATE.match(value):
        return None
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        return None
    return value


def parse_expense_filters(args):
    """Normalize filter query params once.

    -> (filters, error) where
       filters = {"category": str|None, "date_from": str|None, "date_to": str|None}
                 keys match the helper kwargs so routes can do **filters;
                 all values None when error is set (reversed range).
       error   = str|None (friendly message for the {{ error }} pattern).
    """
    category = (args.get("category") or "").strip()
    if category and category not in CATEGORIES:
        category = None
    date_from = _parse_iso_date((args.get("date_from") or "").strip())
    date_to = _parse_iso_date((args.get("date_to") or "").strip())

    error = None
    if date_from and date_to and date_from > date_to:
        error = "Start date must be on or before end date."
        category = date_from = date_to = None

    return (
        {"category": category or None, "date_from": date_from, "date_to": date_to},
        error,
    )


def _expense_filters_sql(category=None, date_from=None, date_to=None):
    """Return (sql_fragment, params) to append after `WHERE user_id = ?`."""
    clauses, params = [], []
    if category:
        clauses.append("AND category = ?")
        params.append(category)
    if date_from:
        clauses.append("AND date >= ?")
        params.append(date_from)
    if date_to:
        clauses.append("AND date <= ?")
        params.append(date_to)
    return " ".join(clauses), params


def describe_filters(filters):
    """Human summary of active filters, e.g. 'Food, from 2026-09-01 to 2026-09-30'."""
    parts = []
    if filters.get("category"):
        parts.append(filters["category"])
    if filters.get("date_from") and filters.get("date_to"):
        parts.append(f"from {filters['date_from']} to {filters['date_to']}")
    elif filters.get("date_from"):
        parts.append(f"from {filters['date_from']}")
    elif filters.get("date_to"):
        parts.append(f"up to {filters['date_to']}")
    return ", ".join(parts)


def filter_query_string(filters):
    """Query string (no leading ?) for active filters, '' when none."""
    return urlencode({k: v for k, v in filters.items() if v})


# ------------------------------------------------------------------ #
# Session hardening                                                   #
# ------------------------------------------------------------------ #

@app.before_request
def load_user():
    """Attach the signed-in user to g, or drop a stale session cookie."""
    g.user = None
    if request.endpoint == "static" or "user_id" not in session:
        return
    conn = get_db()
    try:
        g.user = conn.execute(
            "SELECT id, name, email, created_at, password_version FROM users WHERE id = ?",
            (session["user_id"],),
        ).fetchone()
    finally:
        conn.close()
    # Drop sessions minted against an older password (stolen-cookie remediation).
    if g.user is None or session.get("pw_version") != g.user["password_version"]:
        session.clear()
        g.user = None


# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #

@app.route("/")
def landing():
    return render_template("landing.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        if "user_id" in session:
            return redirect(url_for("profile"))
        return render_template("register.html")

    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")

    if not name:
        return render_template("register.html", error="Please enter your name."), 400
    if not email:
        return render_template("register.html", error="Please enter your email address."), 400
    if not is_valid_email(email):
        return render_template("register.html", error="Please enter a valid email address."), 400
    if len(password) < 8:
        return render_template("register.html", error="Password must be at least 8 characters."), 400

    conn = get_db()
    try:
        existing = conn.execute(
            "SELECT 1 FROM users WHERE email = ?", (email,)
        ).fetchone()
        if existing:
            return render_template(
                "register.html", error="An account with that email already exists."
            ), 400
        try:
            conn.execute(
                "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
                (name, email, generate_password_hash(password)),
            )
            conn.commit()
        except sqlite3.IntegrityError:
            return render_template(
                "register.html", error="An account with that email already exists."
            ), 400
    finally:
        conn.close()

    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        if "user_id" in session:
            return redirect(url_for("profile"))
        success = None
        if request.args.get("reset") == "1":
            success = "Your password has been reset. Sign in with your new password."
        return render_template("login.html", success=success)

    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")

    if not email or not password:
        return render_template(
            "login.html", error="Please enter your email and password."
        ), 400

    conn = get_db()
    try:
        row = conn.execute(
            "SELECT id, password_hash, password_version FROM users WHERE email = ?",
            (email,),
        ).fetchone()
    finally:
        conn.close()

    if row is None or not check_password_hash(row["password_hash"], password):
        return render_template("login.html", error="Invalid email or password."), 400

    session.clear()
    session["user_id"] = row["id"]
    session["pw_version"] = row["password_version"]
    return redirect(url_for("profile"))


# Lightweight throttle for the public reset form (in-memory, per process).
_RESET_ATTEMPTS = {}  # ip -> [timestamps]
_RESET_LIMIT = 5
_RESET_WINDOW_SECONDS = 60


def _reset_throttled(ip, limit=_RESET_LIMIT, window=_RESET_WINDOW_SECONDS):
    """True when this IP has posted too many resets inside the window."""
    now = time.time()
    hits = [t for t in _RESET_ATTEMPTS.get(ip, []) if now - t < window]
    if len(hits) >= limit:
        _RESET_ATTEMPTS[ip] = hits
        return True
    hits.append(now)
    _RESET_ATTEMPTS[ip] = hits
    return False


# SECURITY (learning project): this reset has NO email/OTP verification —
# anyone who knows an account's email can set a new password for it.
# Real apps email a single-use token instead. Never ship this to production.
@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if "user_id" in session:
        return redirect(url_for("profile"))
    if request.method == "GET":
        return render_template("forgot_password.html")

    if _reset_throttled(request.remote_addr or "unknown"):
        return render_template(
            "forgot_password.html",
            error="Too many reset attempts. Please wait a minute and try again.",
        ), 429

    email = request.form.get("email", "").strip().lower()
    new = request.form.get("new_password", "")
    confirm = request.form.get("confirm_password", "")

    if not email or not new or not confirm:
        return render_template(
            "forgot_password.html", error="Please fill in all fields."
        ), 400
    if not is_valid_email(email):
        return render_template(
            "forgot_password.html", error="Please enter a valid email address."
        ), 400
    if len(new) < 8:
        return render_template(
            "forgot_password.html", error="Password must be at least 8 characters."
        ), 400
    if new != confirm:
        return render_template(
            "forgot_password.html", error="New passwords do not match."
        ), 400

    conn = get_db()
    try:
        row = conn.execute(
            "SELECT id FROM users WHERE email = ?", (email,)
        ).fetchone()
        if row is None:
            return render_template(
                "forgot_password.html",
                error="No account found with that email address.",
            ), 400
        # password_version bump invalidates every existing session on next request.
        conn.execute(
            "UPDATE users SET password_hash = ?, password_version = password_version + 1 "
            "WHERE id = ?",
            (generate_password_hash(new), row["id"]),
        )
        conn.commit()
    finally:
        conn.close()

    return redirect(url_for("login", reset=1))


@app.route("/terms")
def terms():
    return render_template("terms.html")


# ------------------------------------------------------------------ #
# Placeholder routes — students will implement these                  #
# ------------------------------------------------------------------ #

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("landing"))


# ------------------------------------------------------------------ #
# Profile data helpers + JSON endpoints (Step 5, Scope B)             #
# Each block is filled by one subagent's snippet; orchestrator splices #
# ------------------------------------------------------------------ #

# ===== BEGIN STEP5 SUMMARY-STATS (subagent-2) =====
def get_summary_stats(user_id, category=None, date_from=None, date_to=None):
    """Return {"expense_count": <int>, "total_spend": <float>} for one user.

    Optional category / date_from / date_to narrow the result (inclusive ISO dates).
    """
    frag, params = _expense_filters_sql(category, date_from, date_to)
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT COUNT(*) AS n, COALESCE(SUM(amount), 0) AS total "
            "FROM expenses WHERE user_id = ? " + frag,
            (user_id, *params),
        ).fetchone()
    finally:
        conn.close()
    count = row["n"]
    total = float(row["total"])
    return {
        "expense_count": count,
        "total_spend": total,
        "average_spend": (total / count) if count else 0.0,
    }


@app.route("/api/profile/stats")
@login_required
def api_profile_stats():
    """JSON summary stats for the signed-in user."""
    filters, _ = parse_expense_filters(request.args)
    return jsonify(get_summary_stats(g.user["id"], **filters))
# ===== END STEP5 SUMMARY-STATS =====

# ===== BEGIN STEP5 CATEGORY-BREAKDOWN (subagent-3) =====
def get_category_breakdown(user_id, category=None, date_from=None, date_to=None):
    """Return list[dict] with keys: category, count, total, bar_pct.

    bar_pct is relative to the largest category in the (filtered) result.
    """
    frag, params = _expense_filters_sql(category, date_from, date_to)
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT category, COUNT(*) AS n, COALESCE(SUM(amount), 0) AS total "
            "FROM expenses WHERE user_id = ? " + frag + " "
            "GROUP BY category ORDER BY total DESC",
            (user_id, *params),
        ).fetchall()
    finally:
        conn.close()

    max_total = max((row["total"] for row in rows), default=0)
    grand_total = sum(row["total"] for row in rows)
    breakdown = [
        {
            "category": row["category"],
            "count": row["n"],
            "total": row["total"],
            "bar_pct": round(row["total"] / max_total * 100, 1) if max_total else 0,
            "share_pct": (
                round(row["total"] / grand_total * 100, 1) if grand_total else 0
            ),
        }
        for row in rows
    ]
    return breakdown


@app.route("/api/profile/breakdown")
@login_required
def api_profile_breakdown():
    """JSON: {"breakdown": [...]} for the signed-in user."""
    filters, _ = parse_expense_filters(request.args)
    return jsonify({"breakdown": get_category_breakdown(g.user["id"], **filters)})
# ===== END STEP5 CATEGORY-BREAKDOWN =====

# ===== BEGIN STEP5 TRANSACTION-HISTORY (subagent-1) =====
def get_recent_transactions(
    user_id, limit=5, category=None, date_from=None, date_to=None
):
    """Return up to *limit* of the user's expenses, newest first.
    -> list[dict] with keys: id, amount, category, date, description
    """
    frag, params = _expense_filters_sql(category, date_from, date_to)
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT id, amount, category, date, description "
            "FROM expenses WHERE user_id = ? " + frag + " "
            "ORDER BY date DESC, id DESC LIMIT ?",
            (user_id, *params, limit),
        ).fetchall()
    finally:
        conn.close()
    return [dict(row) for row in rows]


def _filter_template_context(filters, error, filter_action):
    """Shared context for pages that render the filter bar."""
    return {
        "categories": CATEGORIES,
        "filters": filters,
        "filters_active": any(filters.values()),
        "filter_summary": describe_filters(filters),
        "filter_qs": filter_query_string(filters),
        "error": error,
        "filter_action": filter_action,
    }


@app.route("/profile/history")
@login_required
def profile_history():
    """Server-rendered full transaction history page."""
    filters, error = parse_expense_filters(request.args)
    transactions = get_recent_transactions(g.user["id"], limit=100, **filters)
    return render_template(
        "profile_history.html",
        transactions=transactions,
        **_filter_template_context(filters, error, url_for("profile_history")),
    )


@app.route("/api/profile/history")
@login_required
def api_profile_history():
    """JSON: {"transactions": [...], "count": <int>}"""
    filters, _ = parse_expense_filters(request.args)
    limit = request.args.get("limit", 20, type=int)
    limit = max(1, min(limit or 20, 100))
    transactions = get_recent_transactions(g.user["id"], limit=limit, **filters)
    return jsonify({"transactions": transactions, "count": len(transactions)})
# ===== END STEP5 TRANSACTION-HISTORY =====


@app.route("/profile")
@login_required
def profile():
    filters, error = parse_expense_filters(request.args)
    stats = get_summary_stats(g.user["id"], **filters)
    breakdown = get_category_breakdown(g.user["id"], **filters)
    recent_transactions = get_recent_transactions(g.user["id"], limit=5, **filters)
    expense_count = stats["expense_count"]
    total_spend = stats["total_spend"]
    average_spend = stats["average_spend"]

    # Unfiltered count drives the "has any expenses ever" gate so a filtered
    # empty result never falls through to the no-expenses-yet empty state.
    if any(filters.values()):
        total_expense_count = get_summary_stats(g.user["id"])["expense_count"]
    else:
        total_expense_count = expense_count

    top_category = breakdown[0] if breakdown else None
    donut = build_donut(breakdown)

    member_since = None
    if g.user["created_at"]:
        try:
            member_since = datetime.strptime(
                g.user["created_at"], "%Y-%m-%d %H:%M:%S"
            ).strftime("%b %Y")
        except ValueError:
            member_since = None

    return render_template(
        "profile.html",
        member_since=member_since,
        expense_count=expense_count,
        total_expense_count=total_expense_count,
        total_spend=total_spend,
        average_spend=average_spend,
        top_category=top_category,
        donut=donut,
        breakdown=breakdown,
        recent_transactions=recent_transactions,
        **_filter_template_context(filters, error, url_for("profile")),
    )


# ------------------------------------------------------------------ #
# Account management (Step 5, Scope A) — orchestrator-owned            #
# ------------------------------------------------------------------ #

@app.route("/profile/edit", methods=["GET", "POST"])
@login_required
def edit_profile():
    if request.method == "GET":
        return render_template(
            "profile_edit.html", name=g.user["name"], email=g.user["email"]
        )

    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip().lower()

    if not name:
        return render_template(
            "profile_edit.html", name=name, email=email, error="Please enter your name."
        ), 400
    if not email:
        return render_template(
            "profile_edit.html",
            name=name,
            email=email,
            error="Please enter your email address.",
        ), 400
    if not is_valid_email(email):
        return render_template(
            "profile_edit.html",
            name=name,
            email=email,
            error="Please enter a valid email address.",
        ), 400

    conn = get_db()
    try:
        taken = conn.execute(
            "SELECT 1 FROM users WHERE email = ? AND id != ?", (email, g.user["id"])
        ).fetchone()
        if taken:
            return render_template(
                "profile_edit.html",
                name=name,
                email=email,
                error="An account with that email already exists.",
            ), 400
        try:
            conn.execute(
                "UPDATE users SET name = ?, email = ? WHERE id = ?",
                (name, email, g.user["id"]),
            )
            conn.commit()
        except sqlite3.IntegrityError:
            return render_template(
                "profile_edit.html",
                name=name,
                email=email,
                error="An account with that email already exists.",
            ), 400
    finally:
        conn.close()

    return redirect(url_for("profile"))


@app.route("/profile/password", methods=["GET", "POST"])
@login_required
def change_password():
    if request.method == "GET":
        return render_template("profile_password.html")

    current = request.form.get("current_password", "")
    new = request.form.get("new_password", "")
    confirm = request.form.get("confirm_password", "")

    if not current or not new or not confirm:
        return render_template(
            "profile_password.html", error="Please fill in all fields."
        ), 400

    conn = get_db()
    try:
        row = conn.execute(
            "SELECT password_hash FROM users WHERE id = ?", (g.user["id"],)
        ).fetchone()

        if row is None or not check_password_hash(row["password_hash"], current):
            return render_template(
                "profile_password.html", error="Your current password is incorrect."
            ), 400
        if len(new) < 8:
            return render_template(
                "profile_password.html",
                error="Password must be at least 8 characters.",
            ), 400
        if new != confirm:
            return render_template(
                "profile_password.html", error="New passwords do not match."
            ), 400

        conn.execute(
            "UPDATE users SET password_hash = ?, password_version = password_version + 1 "
            "WHERE id = ?",
            (generate_password_hash(new), g.user["id"]),
        )
        new_version = conn.execute(
            "SELECT password_version FROM users WHERE id = ?", (g.user["id"],)
        ).fetchone()["password_version"]
        conn.commit()
    finally:
        conn.close()

    # Keep the current session alive; other sessions die on next request.
    session["pw_version"] = new_version
    return redirect(url_for("profile"))


@app.route("/profile/delete", methods=["POST"])
@login_required
def delete_account():
    conn = get_db()
    try:
        # expenses first — the FK has no ON DELETE CASCADE and get_db() sets
        # PRAGMA foreign_keys = ON, so deleting the user first would raise.
        conn.execute("DELETE FROM expenses WHERE user_id = ?", (g.user["id"],))
        conn.execute("DELETE FROM users WHERE id = ?", (g.user["id"],))
        conn.commit()
    finally:
        conn.close()

    session.clear()
    return redirect(url_for("landing"))


@app.route("/expenses/add")
def add_expense():
    return "Add expense — coming in Step 7"


@app.route("/expenses/<int:id>/edit")
def edit_expense(id):
    return "Edit expense — coming in Step 8"


@app.route("/expenses/<int:id>/delete")
def delete_expense(id):
    return "Delete expense — coming in Step 9"


# ------------------------------------------------------------------ #
# Database startup — schema + seed data ready before routes are used  #
# ------------------------------------------------------------------ #

with app.app_context():
    init_db()
    seed_db()


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
