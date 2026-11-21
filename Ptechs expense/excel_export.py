"""excel_export.py - writes expenses to an Excel (.xlsx) file.

Needs two packages:  openpyxl  and  pillow  (pillow is what lets Excel files
contain pictures such as the logo).
Install them with:  python -m pip install openpyxl pillow
"""

from datetime import datetime
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill

# The logo is looked for in this order. The big one gives the sharpest picture.
LOGO_FILES = [
    Path(__file__).with_name("ptechs_logo_512.png"),
    Path(__file__).with_name("logo.png"),
]
LOGO_SIZE = 56  # how big the logo appears in Excel, in pixels

HEADER_ROW = 4  # rows 1-2 hold the logo and title, row 3 is left empty


def add_logo(ws):
    """Put the logo in cell A1. Return True if it worked, False if not."""
    logo_path = next((path for path in LOGO_FILES if path.exists()), None)
    if logo_path is None:
        return False  # no logo file in the folder

    try:
        from openpyxl.drawing.image import Image
        image = Image(str(logo_path))
    except Exception:
        return False  # most likely pillow is not installed

    image.width = LOGO_SIZE
    image.height = LOGO_SIZE
    ws.add_image(image, "A1")
    return True


def export_to_excel(rows, filepath):
    """Save rows (as returned by database.get_expenses) to an Excel file."""
    wb = Workbook()
    ws = wb.active
    ws.title = "Expenses"

    # Rows 1-2: logo, title and the date the report was made
    has_logo = add_logo(ws)
    title_column = 2 if has_logo else 1  # leave column A for the logo
    ws.row_dimensions[1].height = 44  # tall enough for the logo

    title = ws.cell(row=1, column=title_column, value="Ptechs Expense Report")
    title.font = Font(bold=True, size=16)
    title.alignment = Alignment(vertical="center")

    stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    subtitle = ws.cell(row=2, column=title_column, value=f"Generated {stamp}")
    subtitle.font = Font(size=9, color="666666")

    # Header row
    headers = ["Date", "Category", "Description", "Amount"]
    header_fill = PatternFill("solid", fgColor="D9E1F2")
    for column, text in enumerate(headers, start=1):
        cell = ws.cell(row=HEADER_ROW, column=column, value=text)
        cell.font = Font(bold=True)
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center")

    # One row per expense (the id is left out of the report)
    first_row = HEADER_ROW + 1
    for index, (_id, date_text, category, description, amount) in enumerate(rows):
        row = first_row + index
        # Real dates (not text) so Excel can sort and filter them properly
        real_date = datetime.strptime(date_text, "%Y-%m-%d").date()
        date_cell = ws.cell(row=row, column=1, value=real_date)
        date_cell.number_format = "yyyy-mm-dd"
        date_cell.alignment = Alignment(horizontal="center")
        ws.cell(row=row, column=2, value=category)
        ws.cell(row=row, column=3, value=description)
        ws.cell(row=row, column=4, value=amount).number_format = "#,##0.00"

    last_row = first_row + len(rows) - 1

    # Total row, using an Excel formula so it stays correct if you edit amounts
    total_row = last_row + 1
    ws.cell(row=total_row, column=3, value="Total").font = Font(bold=True)
    total_cell = ws.cell(row=total_row, column=4,
                         value=f"=SUM(D{first_row}:D{last_row})")
    total_cell.font = Font(bold=True)
    total_cell.number_format = "#,##0.00"

    # Column widths, and keep the logo and header visible while scrolling
    for letter, width in zip("ABCD", (14, 16, 40, 14)):
        ws.column_dimensions[letter].width = width
    ws.freeze_panes = f"A{first_row}"

    wb.save(filepath)