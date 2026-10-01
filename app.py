import os
import sqlite3
from datetime import datetime
from functools import wraps

from flask import Flask, g, jsonify, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from database.db import get_db, init_db, seed_db

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
            "SELECT id, name, email, created_at FROM users WHERE id = ?",
            (session["user_id"],),
        ).fetchone()
    finally:
        conn.close()
    if g.user is None:
        session.clear()


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
        return render_template("login.html")

    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")

    if not email or not password:
        return render_template(
            "login.html", error="Please enter your email and password."
        ), 400

    conn = get_db()
    try:
        row = conn.execute(
            "SELECT id, password_hash FROM users WHERE email = ?", (email,)
        ).fetchone()
    finally:
        conn.close()

    if row is None or not check_password_hash(row["password_hash"], password):
        return render_template("login.html", error="Invalid email or password."), 400

    session.clear()
    session["user_id"] = row["id"]
    return redirect(url_for("profile"))


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
def get_summary_stats(user_id):
    """Return {"expense_count": <int>, "total_spend": <float>} for one user."""
    conn = get_db()
    try:
        row = conn.execute(
            """
            SELECT COUNT(*) AS n, COALESCE(SUM(amount), 0) AS total
            FROM expenses
            WHERE user_id = ?
            """,
            (user_id,),
        ).fetchone()
    finally:
        conn.close()
    return {"expense_count": row["n"], "total_spend": float(row["total"])}


@app.route("/api/profile/stats")
@login_required
def api_profile_stats():
    """JSON summary stats for the signed-in user."""
    return jsonify(get_summary_stats(g.user["id"]))
# ===== END STEP5 SUMMARY-STATS =====

# ===== BEGIN STEP5 CATEGORY-BREAKDOWN (subagent-3) =====
def get_category_breakdown(user_id):
    """Return list[dict] with keys: category, count, total, bar_pct."""
    conn = get_db()
    try:
        rows = conn.execute(
            """
            SELECT category, COUNT(*) AS n, COALESCE(SUM(amount), 0) AS total
            FROM expenses
            WHERE user_id = ?
            GROUP BY category
            ORDER BY total DESC
            """,
            (user_id,),
        ).fetchall()
    finally:
        conn.close()

    max_total = max((row["total"] for row in rows), default=0)
    breakdown = [
        {
            "category": row["category"],
            "count": row["n"],
            "total": row["total"],
            "bar_pct": round(row["total"] / max_total * 100, 1) if max_total else 0,
        }
        for row in rows
    ]
    return breakdown


@app.route("/api/profile/breakdown")
@login_required
def api_profile_breakdown():
    """JSON: {"breakdown": [...]} for the signed-in user."""
    return jsonify({"breakdown": get_category_breakdown(g.user["id"])})
# ===== END STEP5 CATEGORY-BREAKDOWN =====

# ===== BEGIN STEP5 TRANSACTION-HISTORY (subagent-1) =====
def get_recent_transactions(user_id, limit=5):
    """Return up to *limit* of the user's expenses, newest first.
    -> list[dict] with keys: id, amount, category, date, description
    """
    conn = get_db()
    try:
        rows = conn.execute(
            """
            SELECT id, amount, category, date, description
            FROM expenses
            WHERE user_id = ?
            ORDER BY date DESC, id DESC
            LIMIT ?
            """,
            (user_id, limit),
        ).fetchall()
    finally:
        conn.close()
    return [dict(row) for row in rows]


@app.route("/profile/history")
@login_required
def profile_history():
    """Server-rendered full transaction history page."""
    transactions = get_recent_transactions(g.user["id"], limit=100)
    return render_template("profile_history.html", transactions=transactions)


@app.route("/api/profile/history")
@login_required
def api_profile_history():
    """JSON: {"transactions": [...], "count": <int>}"""
    limit = request.args.get("limit", 20, type=int)
    limit = max(1, min(limit or 20, 100))
    transactions = get_recent_transactions(g.user["id"], limit=limit)
    return jsonify({"transactions": transactions, "count": len(transactions)})
# ===== END STEP5 TRANSACTION-HISTORY =====


@app.route("/profile")
@login_required
def profile():
    stats = get_summary_stats(g.user["id"])
    breakdown = get_category_breakdown(g.user["id"])
    recent_transactions = get_recent_transactions(g.user["id"], limit=5)
    expense_count = stats["expense_count"]
    total_spend = stats["total_spend"]

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
        total_spend=total_spend,
        breakdown=breakdown,
        recent_transactions=recent_transactions,
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
            "UPDATE users SET password_hash = ? WHERE id = ?",
            (generate_password_hash(new), g.user["id"]),
        )
        conn.commit()
    finally:
        conn.close()

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
