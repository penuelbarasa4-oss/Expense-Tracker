"""test_database.py - automatic checks for database.py.

Run them with:   python -m unittest test_database -v
(or open this file in VS Code and press the Run button).

Every test gets its own empty temporary database, so your real
expenses.db is never touched.
"""

import tempfile
import unittest
from pathlib import Path

import database


class DatabaseTests(unittest.TestCase):
    def setUp(self):
        """Runs before EVERY test: point the database at a fresh temp file."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_name = database.DB_NAME
        database.DB_NAME = str(Path(self.temp_dir.name) / "test_expenses.db")
        database.create_table()

    def tearDown(self):
        """Runs after EVERY test: put things back and delete the temp file."""
        database.DB_NAME = self.original_name
        self.temp_dir.cleanup()

    def add_sample_data(self):
        """Four expenses used by several tests (two months, two categories)."""
        database.add_expense("2026-11-21", "Office", "Desk", 2500.00)
        database.add_expense("2026-11-21", "Travel", "Bus fare", 4.00)
        database.add_expense("2026-11-05", "Travel", "Taxi", 20.50)
        database.add_expense("2026-10-15", "Office", "Paper", 12.50)

    # ---------- Creating the table ----------

    def test_create_table_twice_keeps_existing_data(self):
        database.add_expense("2026-11-21", "Office", "Desk", 100)
        database.create_table()  # the app calls this on every start
        self.assertEqual(len(database.get_expenses()), 1)

    def test_empty_database(self):
        self.assertEqual(database.get_expenses(), [])
        self.assertEqual(database.get_total(), 0)
        self.assertEqual(database.get_categories(), [])
        self.assertEqual(database.get_months(), [])
        self.assertEqual(database.get_category_summary(), [])

    # ---------- Add, update, delete ----------

    def test_add_expense_saves_all_fields(self):
        new_id = database.add_expense("2026-11-21", "Office", "Desk", 2500.00)
        self.assertEqual(
            database.get_expenses(),
            [(new_id, "2026-11-21", "Office", "Desk", 2500.00)],
        )

    def test_add_expense_gives_each_expense_its_own_id(self):
        first = database.add_expense("2026-11-21", "Office", "Desk", 1)
        second = database.add_expense("2026-11-21", "Office", "Chair", 1)
        self.assertNotEqual(first, second)

    def test_update_expense_changes_the_row(self):
        expense_id = database.add_expense("2026-11-21", "Office", "Paper", 12.50)
        database.update_expense(expense_id, "2026-11-22", "Travel", "Taxi", 30.00)
        self.assertEqual(
            database.get_expenses(),
            [(expense_id, "2026-11-22", "Travel", "Taxi", 30.00)],
        )

    def test_update_only_changes_the_chosen_expense(self):
        first = database.add_expense("2026-11-21", "Office", "Desk", 100)
        database.add_expense("2026-11-21", "Office", "Chair", 50)
        database.update_expense(first, "2026-11-21", "Office", "Big desk", 120)
        descriptions = sorted(row[3] for row in database.get_expenses())
        self.assertEqual(descriptions, ["Big desk", "Chair"])

    def test_delete_expense_removes_only_that_expense(self):
        first = database.add_expense("2026-11-21", "Office", "Desk", 100)
        database.add_expense("2026-11-21", "Office", "Chair", 50)
        database.delete_expense(first)
        rows = database.get_expenses()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][3], "Chair")

    def test_delete_missing_id_does_not_crash(self):
        database.delete_expense(999)  # nothing with this id exists
        self.assertEqual(database.get_expenses(), [])

    def test_awkward_text_is_saved_safely(self):
        # Apostrophes and SQL-looking text must be stored as plain text
        nasty = "Bob's \"special\" pens; DROP TABLE expenses; --"
        database.add_expense("2026-11-21", "Office", nasty, 5)
        rows = database.get_expenses()
        self.assertEqual(len(rows), 1)       # the table still exists
        self.assertEqual(rows[0][3], nasty)  # and the text is unchanged

    # ---------- Reading and sorting ----------

    def test_expenses_are_newest_date_first(self):
        self.add_sample_data()
        dates = [row[1] for row in database.get_expenses()]
        self.assertEqual(
            dates, ["2026-11-21", "2026-11-21", "2026-11-05", "2026-10-15"])

    def test_same_date_shows_most_recently_added_first(self):
        self.add_sample_data()
        descriptions = [row[3] for row in database.get_expenses()]
        self.assertEqual(descriptions[:2], ["Bus fare", "Desk"])

    # ---------- Totals and filters ----------

    def test_total_of_everything(self):
        self.add_sample_data()
        self.assertAlmostEqual(database.get_total(), 2537.00)

    def test_total_filtered_by_category(self):
        self.add_sample_data()
        self.assertAlmostEqual(database.get_total(category="Travel"), 24.50)

    def test_total_filtered_by_month(self):
        self.add_sample_data()
        self.assertAlmostEqual(database.get_total(month="2026-11"), 2524.50)
        self.assertAlmostEqual(database.get_total(month="2026-10"), 12.50)

    def test_total_filtered_by_category_and_month(self):
        self.add_sample_data()
        self.assertAlmostEqual(database.get_total("Travel", "2026-11"), 24.50)
        self.assertAlmostEqual(database.get_total("Office", "2026-10"), 12.50)
        self.assertEqual(database.get_total("Travel", "2026-10"), 0)

    def test_month_filter_does_not_mix_up_years(self):
        self.add_sample_data()
        database.add_expense("2025-11-10", "Office", "Old chair", 999)
        self.assertAlmostEqual(database.get_total(month="2026-11"), 2524.50)

    def test_get_expenses_with_filters(self):
        self.add_sample_data()
        travel = database.get_expenses(category="Travel")
        self.assertEqual([row[3] for row in travel], ["Bus fare", "Taxi"])
        october = database.get_expenses(month="2026-10")
        self.assertEqual([row[3] for row in october], ["Paper"])
        self.assertEqual(database.get_expenses(category="Salaries"), [])

    def test_build_filter(self):
        self.assertEqual(database.build_filter(), ("", []))
        self.assertEqual(
            database.build_filter(category="Travel"),
            (" WHERE category = ?", ["Travel"]))
        self.assertEqual(
            database.build_filter(month="2026-11"),
            (" WHERE date LIKE ?", ["2026-11-%"]))
        self.assertEqual(
            database.build_filter("Travel", "2026-11"),
            (" WHERE category = ? AND date LIKE ?", ["Travel", "2026-11-%"]))

    # ---------- Lists used by the dropdowns and the summary tab ----------

    def test_categories_are_unique_and_alphabetical(self):
        self.add_sample_data()
        self.assertEqual(database.get_categories(), ["Office", "Travel"])

    def test_months_are_unique_and_newest_first(self):
        self.add_sample_data()
        self.assertEqual(database.get_months(), ["2026-11", "2026-10"])

    def test_category_summary_all_time(self):
        self.add_sample_data()
        self.assertEqual(
            database.get_category_summary(),
            [("Office", 2, 2512.50), ("Travel", 2, 24.50)])

    def test_category_summary_for_one_month(self):
        self.add_sample_data()
        self.assertEqual(
            database.get_category_summary("2026-11"),
            [("Office", 1, 2500.00), ("Travel", 2, 24.50)])

    def test_category_summary_biggest_total_first(self):
        database.add_expense("2026-11-01", "Small", "a", 1)
        database.add_expense("2026-11-01", "Big", "b", 500)
        database.add_expense("2026-11-01", "Medium", "c", 50)
        categories = [row[0] for row in database.get_category_summary()]
        self.assertEqual(categories, ["Big", "Medium", "Small"])

    def test_category_summary_for_month_without_expenses(self):
        self.add_sample_data()
        self.assertEqual(database.get_category_summary("2025-01"), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)