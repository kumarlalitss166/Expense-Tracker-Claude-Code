"""Insert realistic dummy expenses for one user into expense_tracker.db."""

import random
import sys
from datetime import date, timedelta

from database.db import get_db, init_db

# Category -> (min_amount, max_amount, weight)
# Weights: Food most common; Health and Entertainment least.
CATEGORIES = {
    "Food": (50, 800, 30),
    "Transport": (20, 500, 18),
    "Bills": (200, 3000, 14),
    "Health": (100, 2000, 8),
    "Entertainment": (100, 1500, 8),
    "Shopping": (200, 5000, 12),
    "Other": (50, 1000, 10),
}

DESCRIPTIONS = {
    "Food": [
        "Lunch at office canteen", "Dinner with family", "Groceries from local market",
        "Street food — chaat and pav bhaji", "Tea and snacks", "Zomato order",
        "Monthly ration — atta, dal, rice", "Breakfast at tiffin centre",
        "Weekend biryani", "Fruits and vegetables",
    ],
    "Transport": [
        "Auto to office", "Ola ride home", "Monthly bus pass", "Petrol top-up",
        "Metro card recharge", "Cab to airport", "Local train ticket", "Uber to client meeting",
    ],
    "Bills": [
        "Electricity bill", "Mobile recharge", "Broadband payment", "Gas cylinder booking",
        "Water bill", "DTH subscription", "House rent", "Maintenance charges",
    ],
    "Health": [
        "Pharmacy purchase", "Doctor consultation", "Lab tests", "Dental checkup",
        "Ayurvedic medicines", "Health insurance premium", "Gym membership",
    ],
    "Entertainment": [
        "Movie tickets", "Netflix subscription", "Concert tickets", "Amusement park",
        "Cricket match tickets", "Amazon Prime subscription", "Weekend outing",
    ],
    "Shopping": [
        "Kurta from Myntra", "Running shoes", "Mobile accessories", "Home decor",
        "Festival shopping", "Electronics sale pickup", "Gift for friend", "Saree from local store",
    ],
    "Other": [
        "App subscription", "Gift for relative", "Donation", "Stationery",
        "Courier charges", "Temple offering", "Miscellaneous expenses",
    ],
}


def parse_args():
    if len(sys.argv) != 4:
        print("Usage: /seed-expenses <user_id> <count> <months>")
        print("Example: /seed-expenses 1 50 6")
        sys.exit(1)
    try:
        user_id = int(sys.argv[1])
        count = int(sys.argv[2])
        months = int(sys.argv[3])
        if user_id <= 0 or count <= 0 or months <= 0:
            raise ValueError
    except ValueError:
        print("Usage: /seed-expenses <user_id> <count> <months>")
        print("Example: /seed-expenses 1 50 6")
        sys.exit(1)
    return user_id, count, months


def random_date_in_past_months(months: int) -> date:
    today = date.today()
    start = today - timedelta(days=months * 30)
    span = (today - start).days
    return start + timedelta(days=random.randint(0, span))


def build_expense() -> tuple:
    category = random.choices(
        list(CATEGORIES.keys()),
        weights=[w for _, _, w in CATEGORIES.values()],
        k=1,
    )[0]
    lo, hi, _ = CATEGORIES[category]
    amount = round(random.uniform(lo, hi), 2)
    description = random.choice(DESCRIPTIONS[category])
    return category, amount, description


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    user_id, count, months = parse_args()
    init_db()

    conn = get_db()
    try:
        user = conn.execute(
            "SELECT id FROM users WHERE id = ?", (user_id,)
        ).fetchone()
        if user is None:
            print(f"No user found with id {user_id}.")
            sys.exit(1)

        rows = []
        for _ in range(count):
            category, amount, description = build_expense()
            expense_date = random_date_in_past_months(months).isoformat()
            rows.append((user_id, amount, category, expense_date, description))

        try:
            conn.executemany(
                """
                INSERT INTO expenses (user_id, amount, category, date, description)
                VALUES (?, ?, ?, ?, ?)
                """,
                rows,
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise

        dates = sorted(r[3] for r in rows)
        print(f"Inserted {count} expenses for user_id {user_id}.")
        print(f"Date range: {dates[0]} to {dates[-1]}")
        print("\nSample of 5 inserted records:")
        sample = conn.execute(
            """
            SELECT id, amount, category, date, description
            FROM expenses
            WHERE user_id = ?
            ORDER BY date DESC
            LIMIT 5
            """,
            (user_id,),
        ).fetchall()
        for row in sample:
            print(
                f"  id={row['id']} | ₹{row['amount']:.2f} | {row['category']} "
                f"| {row['date']} | {row['description']}"
            )
    finally:
        conn.close()


if __name__ == "__main__":
    main()
