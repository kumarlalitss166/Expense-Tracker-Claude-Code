# Step 1 — Database Setup
# SQLite data layer for Spendly: connection helper, schema creation, dev seed data.

import sqlite3
from datetime import date
from pathlib import Path

from werkzeug.security import generate_password_hash

# Project root — parent of the `database/` package, so the DB path
# does not depend on the current working directory.
DB_PATH = Path(__file__).resolve().parent.parent / "expense_tracker.db"

CATEGORIES = [
    "Food",
    "Transport",
    "Bills",
    "Health",
    "Entertainment",
    "Shopping",
    "Other",
]


def get_db():
    """Open a SQLite connection with row access and foreign keys enabled."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Create the users and expenses tables if they do not already exist."""
    conn = get_db()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TEXT DEFAULT (datetime('now'))
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                amount REAL NOT NULL,
                category TEXT NOT NULL,
                date TEXT NOT NULL,
                description TEXT,
                created_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def seed_db():
    """Insert the demo user and sample expenses once, if the users table is empty."""
    conn = get_db()
    try:
        count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        if count > 0:
            return

        conn.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            ("Demo User", "demo@spendly.com", generate_password_hash("demo123")),
        )
        user_id = conn.execute(
            "SELECT id FROM users WHERE email = ?", ("demo@spendly.com",)
        ).fetchone()["id"]

        today = date.today()
        sample_expenses = [
            (12.50, "Food", 2, "Lunch at the cafe"),
            (45.00, "Transport", 5, "Monthly bus pass top-up"),
            (60.00, "Bills", 8, "Electricity bill"),
            (22.00, "Health", 11, "Pharmacy purchase"),
            (30.00, "Entertainment", 14, "Movie ticket"),
            (55.00, "Shopping", 18, "New running shoes"),
            (4.99, "Other", 22, "App subscription"),
            (18.75, "Food", 26, "Groceries run"),
        ]
        for amount, category, day, description in sample_expenses:
            conn.execute(
                """
                INSERT INTO expenses (user_id, amount, category, date, description)
                VALUES (?, ?, ?, ?, ?)
                """,
                (user_id, amount, category, today.replace(day=day).isoformat(), description),
            )
        conn.commit()
    finally:
        conn.close()
