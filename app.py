import os
import sqlite3
from datetime import datetime
from functools import wraps

from flask import Flask, g, redirect, render_template, request, session, url_for
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
    local, sep, domain = email.partition("@")
    if (
        email.count("@") != 1
        or not local
        or "." not in domain
        or domain.startswith(".")
        or domain.endswith(".")
        or ".." in domain
    ):
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


@app.route("/profile")
@login_required
def profile():
    conn = get_db()
    try:
        stats = conn.execute(
            """
            SELECT COUNT(*) AS n, COALESCE(SUM(amount), 0) AS total
            FROM expenses WHERE user_id = ?
            """,
            (g.user["id"],),
        ).fetchone()
        rows = conn.execute(
            """
            SELECT category, COUNT(*) AS n, COALESCE(SUM(amount), 0) AS total
            FROM expenses WHERE user_id = ?
            GROUP BY category ORDER BY total DESC
            """,
            (g.user["id"],),
        ).fetchall()
    finally:
        conn.close()

    expense_count = stats["n"]
    total_spend = stats["total"]

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
    )


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
