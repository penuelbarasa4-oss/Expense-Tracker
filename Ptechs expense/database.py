"""database.py - the SQLite layer for the Ptechs expense tracker.

This file only talks to the database. No windows, no buttons.
Run it directly (python database.py) to test that everything works.
"""

import sqlite3

DB_NAME = "expenses.db"


def connect():
    """Open a connection to the database file (it is created if missing)."""
    return sqlite3.connect(DB_NAME)


def create_table():
    """Create the expenses table the first time the program runs."""
    conn = connect()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS expenses (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            date        TEXT NOT NULL,      -- stored as YYYY-MM-DD
            category    TEXT NOT NULL,
            description TEXT,
            amount      REAL NOT NULL
        )
        """
    )
    conn.commit()
    conn.close()


def add_expense(date, category, description, amount):
    """Save a new expense and return its id."""
    conn = connect()
    cursor = conn.execute(
        "INSERT INTO expenses (date, category, description, amount) "
        "VALUES (?, ?, ?, ?)",
        (date, category, description, amount),
    )
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()
    return new_id


def build_filter(category=None, month=None):
    """Build the WHERE part of a query from the filters that are set.

    category: e.g. "Travel" (or None for all categories)
    month:    e.g. "2026-11" (or None for all months)
    Returns (where_text, values). The values still go in through ? placeholders.
    """
    conditions = []
    values = []
    if category:
        conditions.append("category = ?")
        values.append(category)
    if month:
        conditions.append("date LIKE ?")
        values.append(month + "-%")  # matches 2026-11-01, 2026-11-02, ...
    where = " WHERE " + " AND ".join(conditions) if conditions else ""
    return where, values


def get_expenses(category=None, month=None):
    """Return expenses as a list of tuples, newest date first.

    Pass category and/or month to only get matching expenses.
    """
    where, values = build_filter(category, month)
    conn = connect()
    rows = conn.execute(
        "SELECT id, date, category, description, amount FROM expenses"
        + where
        + " ORDER BY date DESC, id DESC",
        values,
    ).fetchall()
    conn.close()
    return rows


def get_categories():
    """Return the categories that are actually used, in alphabetical order."""
    conn = connect()
    rows = conn.execute(
        "SELECT DISTINCT category FROM expenses ORDER BY category"
    ).fetchall()
    conn.close()
    return [row[0] for row in rows]


def get_months():
    """Return the months that have expenses, newest first (e.g. '2026-11')."""
    conn = connect()
    rows = conn.execute(
        "SELECT DISTINCT substr(date, 1, 7) FROM expenses "
        "ORDER BY substr(date, 1, 7) DESC"
    ).fetchall()
    conn.close()
    return [row[0] for row in rows]


def get_category_summary(month=None):
    """Return (category, number_of_expenses, total) for each category.

    Biggest total first. Pass month (e.g. '2026-11') for one month only,
    or leave it out to cover all time.
    """
    where, values = build_filter(None, month)
    conn = connect()
    rows = conn.execute(
        "SELECT category, COUNT(*), SUM(amount) FROM expenses"
        + where
        + " GROUP BY category ORDER BY SUM(amount) DESC",
        values,
    ).fetchall()
    conn.close()
    return rows


def update_expense(expense_id, date, category, description, amount):
    """Change an existing expense."""
    conn = connect()
    conn.execute(
        "UPDATE expenses SET date = ?, category = ?, description = ?, amount = ? "
        "WHERE id = ?",
        (date, category, description, amount, expense_id),
    )
    conn.commit()
    conn.close()


def delete_expense(expense_id):
    """Remove an expense."""
    conn = connect()
    conn.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
    conn.commit()
    conn.close()


def get_total(category=None, month=None):
    """Return the sum of the matching expenses (0 if there are none)."""
    where, values = build_filter(category, month)
    conn = connect()
    total = conn.execute(
        "SELECT SUM(amount) FROM expenses" + where, values
    ).fetchone()[0]
    conn.close()
    return total or 0


# ---- Quick test: only runs when you do "python database.py" ----
if __name__ == "__main__":
    create_table()

    first_id = add_expense("2026-11-21", "Office", "Printer paper", 12.50)
    add_expense("2026-11-21", "Travel", "Bus fare", 4.00)

    print("All expenses:")
    for row in get_expenses():
        print(row)

    update_expense(first_id, "2026-11-21", "Office", "Printer paper (A4)", 13.00)
    print("Total:", get_total())

    delete_expense(first_id)
    print("After delete:", get_expenses())