# Ptechs Expense Tracker

A simple desktop app for recording and reviewing company expenses.
Built with Python, tkinter and SQLite.

## Features

- Add, edit and delete expenses (date, category, description, amount)
- Filter the list by category and/or month
- Monthly summary by category, with a bar chart that updates automatically
- Export the current view to a formatted Excel report with the company logo
- Light and dark mode (the choice is remembered)
- All data is stored locally in a single SQLite file (`expenses.db`)

## Requirements

- Python 3.10 or newer (tkinter is included with the standard Windows installer)
- The packages in `requirements.txt` (`openpyxl` and `pillow`)

## Setup

```
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
```

## Run

```
python app.py
```

The database file `expenses.db` is created automatically the first time the
app starts. It is not part of this repository.

## Run the tests

```
python -m unittest test_database -v
```

The tests use a temporary database, so your real data is never touched.

## Files

| File | Purpose |
| --- | --- |
| `app.py` | The window (tabs, form, table, chart, dark mode) |
| `database.py` | All SQLite code: saving, loading, filters, totals |
| `excel_export.py` | Writes the Excel report |
| `test_database.py` | Automatic tests for `database.py` |
| `logo.png`, `ptechs_logo_512.png` | The logo used in the app and the Excel report |

## Backups

All expenses live in the one `expenses.db` file. Copy it somewhere safe from
time to time.
