"""Insert one random Indian dummy user into expense_tracker.db."""

import random
import re
from datetime import datetime

from werkzeug.security import generate_password_hash

from database.db import get_db, init_db

FIRST_NAMES = [
    "Aarav", "Vivaan", "Aditya", "Arjun", "Rohan", "Karan", "Rahul", "Vikram",
    "Ananya", "Diya", "Ishita", "Kavya", "Meera", "Priya", "Sneha", "Tanvi",
    "Harshit", "Nikhil", "Siddharth", "Varun", "Pooja", "Neha", "Ritu", "Shreya",
    "Manish", "Sanjay", "Amit", "Deepak", "Suresh", "Ravi", "Asha", "Sunita",
    "Gurpreet", "Harleen", "Arnav", "Ishaan", "Lakshmi", "Aryan", "Karthik", "Divya",
]

LAST_NAMES = [
    "Sharma", "Verma", "Iyer", "Nair", "Reddy", "Patel", "Gupta", "Mehta",
    "Singh", "Kaur", "Khan", "Chopra", "Malhotra", "Kapoor", "Joshi", "Desai",
    "Chatterjee", "Banerjee", "Mukherjee", "Das", "Bose", "Rao", "Kulkarni", "Deshpande",
    "Menon", "Pillai", "Naidu", "Reddy", "Agarwal", "Bansal", "Sinha", "Mishra",
    "Pandey", "Shukla", "Yadav", "Chauhan", "Rathore", "Bhat", "Hegde", "Shetty",
]


def slug(name: str) -> str:
    return re.sub(r"[^a-z]", "", name.lower())


def unique_email(conn, first: str, last: str) -> str:
    first_slug, last_slug = slug(first), slug(last)
    for _ in range(50):
        suffix = random.randint(10, 999)
        email = f"{first_slug}.{last_slug}{suffix}@gmail.com"
        exists = conn.execute(
            "SELECT 1 FROM users WHERE email = ?", (email,)
        ).fetchone()
        if not exists:
            return email
    raise RuntimeError("Could not generate a unique email")


def main() -> None:
    init_db()
    first = random.choice(FIRST_NAMES)
    last = random.choice(LAST_NAMES)
    name = f"{first} {last}"
    password_hash = generate_password_hash("password123")
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn = get_db()
    try:
        email = unique_email(conn, first, last)
        cur = conn.execute(
            """
            INSERT INTO users (name, email, password_hash, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (name, email, password_hash, created_at),
        )
        conn.commit()
        user_id = cur.lastrowid
    finally:
        conn.close()

    print("id:", user_id)
    print("name:", name)
    print("email:", email)


if __name__ == "__main__":
    main()
