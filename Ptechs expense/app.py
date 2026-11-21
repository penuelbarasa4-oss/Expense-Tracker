"""app.py - the tkinter window for the Ptechs expense tracker.

Needs database.py and excel_export.py in the same folder.
Run this file to start the app.
"""

import json
import math
import tkinter as tk
from datetime import date, datetime
from pathlib import Path
from tkinter import ttk, messagebox, filedialog

import database
import excel_export

CATEGORIES = ["Office", "Travel", "Utilities", "Salaries", "Equipment", "Other"]

# The dark-mode choice is remembered in this little file next to app.py
SETTINGS_FILE = Path(__file__).with_name("settings.json")

# Put your logo in the project folder with this name (PNG format)
LOGO_FILE = Path(__file__).with_name("logo.png")
LOGO_HEIGHT = 48  # logos taller than this are shrunk (48 = shown at real size)

# One set of colours per mode. apply_theme() paints the whole app with these.
LIGHT = {
    "bg": "#f3f3f3", "fg": "#1f1f1f", "muted": "#6b6b6b", "field": "#ffffff",
    "button": "#e6e6e6", "hover": "#d6d6d6", "border": "#bdbdbd",
    "select": "#cfe3fa", "header": "#d9e1f2", "grid": "#dddddd",
}
DARK = {
    "bg": "#1e1e1e", "fg": "#e8e8e8", "muted": "#9a9a9a", "field": "#2b2b2b",
    "button": "#3a3a3a", "hover": "#4a4a4a", "border": "#555555",
    "select": "#264f78", "header": "#333b4a", "grid": "#3a3a3a",
}

# Bar colours for the chart (they work on both light and dark backgrounds)
CHART_COLORS = ["#4e79a7", "#f28e2b", "#59a14f", "#e15759",
                "#b07aa1", "#76b7b2", "#edc948"]


# ---------- Small helper functions ----------

def load_settings():
    try:
        return json.loads(SETTINGS_FILE.read_text())
    except (OSError, ValueError):
        return {}  # no file yet, or it is damaged: start with defaults


def save_settings(settings):
    try:
        SETTINGS_FILE.write_text(json.dumps(settings))
    except OSError:
        pass  # not being able to remember the theme is not worth a crash


def nice_max(value):
    """Round a number up to a tidy chart maximum (2,500 -> 3,000)."""
    if value <= 0:
        return 1
    step = 10 ** math.floor(math.log10(value))
    return math.ceil(value / step) * step


def format_axis(value):
    if value == int(value):
        return f"{value:,.0f}"
    return f"{value:,.2f}"


class ExpenseApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Ptechs Expense Tracker")
        self.root.geometry("860x660")
        self.root.minsize(760, 560)

        self.settings = load_settings()
        self.dark = bool(self.settings.get("dark_mode", False))

        self.selected_id = None      # id of the expense chosen in the table
        self.active_category = None  # current filter (None = no filter)
        self.active_month = None
        self.summary_rows = []       # data behind the summary table and chart
        self.comboboxes = []         # remembered so the theme can colour them

        self.build_top_bar()

        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.expenses_tab = ttk.Frame(self.notebook, padding=10)
        self.summary_tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.expenses_tab, text="Expenses")
        self.notebook.add(self.summary_tab, text="Summary")

        self.build_form(self.expenses_tab)
        self.build_filter(self.expenses_tab)
        self.build_table(self.expenses_tab)
        self.build_total(self.expenses_tab)
        self.build_summary_tab(self.summary_tab)

        self.apply_theme()
        self.refresh()

    # ---------- Building the window ----------

    def build_top_bar(self):
        bar = ttk.Frame(self.root)
        bar.pack(fill="x", padx=10, pady=10)
        self.load_logo(bar)
        ttk.Label(bar, text="Ptechs Expense Tracker",
                  font=("Segoe UI", 14, "bold")).pack(side="left")
        self.theme_button = ttk.Button(bar, command=self.toggle_theme)
        self.theme_button.pack(side="right")

    def load_logo(self, parent):
        """Show logo.png (if it exists) in the top bar and as the window icon."""
        # We keep the image in self.logo_image on purpose: if it were only a
        # local variable, Python would throw it away and it would not appear.
        self.logo_image = None
        if not LOGO_FILE.exists():
            return  # no logo file yet: the app simply runs without one
        try:
            image = tk.PhotoImage(file=str(LOGO_FILE))
        except tk.TclError:
            return  # tkinter could not read the file (it must be a real PNG)

        # tkinter can only shrink by whole numbers (1/2, 1/3, ...)
        factor = max(1, math.ceil(image.height() / LOGO_HEIGHT))
        self.logo_image = image.subsample(factor)
        self.root.iconphoto(True, image)  # small icon in the title bar / taskbar
        ttk.Label(parent, image=self.logo_image).pack(side="left", padx=(0, 10))

    def build_form(self, parent):
        form = ttk.LabelFrame(parent, text="Expense", padding=10)
        form.pack(fill="x", pady=(0, 10))

        self.date_var = tk.StringVar(value=date.today().isoformat())
        self.category_var = tk.StringVar()
        self.description_var = tk.StringVar()
        self.amount_var = tk.StringVar()

        ttk.Label(form, text="Date (YYYY-MM-DD)").grid(row=0, column=0, sticky="w")
        ttk.Label(form, text="Category").grid(row=0, column=1, sticky="w")
        ttk.Label(form, text="Description").grid(row=0, column=2, sticky="w")
        ttk.Label(form, text="Amount").grid(row=0, column=3, sticky="w")

        ttk.Entry(form, textvariable=self.date_var, width=18).grid(
            row=1, column=0, padx=5, pady=5)
        category_box = ttk.Combobox(form, textvariable=self.category_var,
                                    values=CATEGORIES, width=16)
        category_box.grid(row=1, column=1, padx=5, pady=5)
        self.comboboxes.append(category_box)
        ttk.Entry(form, textvariable=self.description_var, width=32).grid(
            row=1, column=2, padx=5, pady=5)
        ttk.Entry(form, textvariable=self.amount_var, width=12).grid(
            row=1, column=3, padx=5, pady=5)

        buttons = ttk.Frame(form)
        buttons.grid(row=2, column=0, columnspan=4, sticky="w", pady=(10, 0))
        ttk.Button(buttons, text="Add", command=self.on_add).pack(side="left", padx=5)
        ttk.Button(buttons, text="Update", command=self.on_update).pack(side="left", padx=5)
        ttk.Button(buttons, text="Delete", command=self.on_delete).pack(side="left", padx=5)
        ttk.Button(buttons, text="Clear", command=self.clear_form).pack(side="left", padx=5)

    def build_filter(self, parent):
        bar = ttk.LabelFrame(parent, text="Filter", padding=10)
        bar.pack(fill="x", pady=(0, 10))

        self.filter_category_var = tk.StringVar(value="All")
        self.filter_month_var = tk.StringVar()

        ttk.Label(bar, text="Category").pack(side="left")
        self.filter_category_box = ttk.Combobox(
            bar, textvariable=self.filter_category_var,
            values=["All"], width=16, state="readonly")
        self.filter_category_box.pack(side="left", padx=(5, 15))
        self.comboboxes.append(self.filter_category_box)

        ttk.Label(bar, text="Month (YYYY-MM)").pack(side="left")
        ttk.Entry(bar, textvariable=self.filter_month_var, width=10).pack(
            side="left", padx=(5, 15))

        ttk.Button(bar, text="Apply filter", command=self.apply_filter).pack(
            side="left", padx=5)
        ttk.Button(bar, text="Show all", command=self.reset_filter).pack(
            side="left", padx=5)
        ttk.Button(bar, text="Export to Excel", command=self.on_export).pack(
            side="right", padx=5)

    def build_table(self, parent):
        frame = ttk.Frame(parent)
        frame.pack(fill="both", expand=True)

        columns = ("id", "date", "category", "description", "amount")
        self.tree = ttk.Treeview(frame, columns=columns, show="headings",
                                 selectmode="browse")

        headings = {"id": "ID", "date": "Date", "category": "Category",
                    "description": "Description", "amount": "Amount"}
        widths = {"id": 40, "date": 100, "category": 110,
                  "description": 330, "amount": 90}
        for col in columns:
            self.tree.heading(col, text=headings[col])
            self.tree.column(col, width=widths[col], anchor="w")

        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # When the user clicks a row, copy it into the form
        self.tree.bind("<<TreeviewSelect>>", self.on_select)

    def build_total(self, parent):
        self.total_label = ttk.Label(parent, text="Total: 0.00",
                                     font=("Segoe UI", 12, "bold"))
        self.total_label.pack(anchor="e", pady=(10, 0))

    def build_summary_tab(self, parent):
        top = ttk.Frame(parent)
        top.pack(fill="x")

        ttk.Label(top, text="Period").pack(side="left")
        self.period_var = tk.StringVar()
        self.period_box = ttk.Combobox(top, textvariable=self.period_var,
                                       state="readonly", width=14)
        self.period_box.pack(side="left", padx=8)
        self.period_box.bind("<<ComboboxSelected>>",
                             lambda event: self.refresh_summary())
        self.comboboxes.append(self.period_box)

        self.summary_total_label = ttk.Label(top, text="",
                                             font=("Segoe UI", 11, "bold"))
        self.summary_total_label.pack(side="right")

        # Table: one row per category
        table_frame = ttk.Frame(parent)
        table_frame.pack(fill="x", pady=10)

        columns = ("category", "count", "total", "share")
        self.summary_tree = ttk.Treeview(table_frame, columns=columns,
                                         show="headings", height=6,
                                         selectmode="none")
        headings = {"category": "Category", "count": "Expenses",
                    "total": "Total", "share": "Share"}
        widths = {"category": 240, "count": 90, "total": 140, "share": 90}
        for col in columns:
            self.summary_tree.heading(col, text=headings[col])
            anchor = "w" if col == "category" else "e"
            self.summary_tree.column(col, width=widths[col], anchor=anchor)

        scrollbar = ttk.Scrollbar(table_frame, orient="vertical",
                                  command=self.summary_tree.yview)
        self.summary_tree.configure(yscrollcommand=scrollbar.set)
        self.summary_tree.pack(side="left", fill="x", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Chart: a plain canvas we draw on ourselves (no extra libraries needed)
        self.chart = tk.Canvas(parent, height=260, highlightthickness=0)
        self.chart.pack(fill="both", expand=True)
        # Redraw whenever the window (and so the canvas) changes size
        self.chart.bind("<Configure>", lambda event: self.draw_chart())

    # ---------- Look and feel (light / dark) ----------

    def apply_theme(self):
        c = DARK if self.dark else LIGHT
        style = ttk.Style()
        style.theme_use("clam")  # the built-in theme that lets us set every colour

        self.root.configure(background=c["bg"])
        style.configure(".", background=c["bg"], foreground=c["fg"],
                        fieldbackground=c["field"], bordercolor=c["border"],
                        troughcolor=c["bg"])

        style.configure("TFrame", background=c["bg"])
        style.configure("TLabel", background=c["bg"], foreground=c["fg"])
        style.configure("TLabelframe", background=c["bg"], bordercolor=c["border"])
        style.configure("TLabelframe.Label", background=c["bg"], foreground=c["fg"])

        style.configure("TButton", background=c["button"], foreground=c["fg"],
                        bordercolor=c["border"], lightcolor=c["button"],
                        darkcolor=c["button"], focuscolor=c["button"],
                        padding=(10, 4))
        style.map("TButton", background=[("active", c["hover"]),
                                         ("pressed", c["hover"])])

        style.configure("TEntry", fieldbackground=c["field"], foreground=c["fg"],
                        insertcolor=c["fg"], bordercolor=c["border"])
        style.configure("TCombobox", fieldbackground=c["field"],
                        background=c["button"], foreground=c["fg"],
                        arrowcolor=c["fg"], bordercolor=c["border"],
                        selectbackground=c["field"], selectforeground=c["fg"])
        style.map("TCombobox",
                  fieldbackground=[("readonly", c["field"])],
                  foreground=[("readonly", c["fg"])],
                  selectbackground=[("readonly", c["field"])],
                  selectforeground=[("readonly", c["fg"])])

        style.configure("Treeview", background=c["field"], fieldbackground=c["field"],
                        foreground=c["fg"], bordercolor=c["border"], rowheight=26)
        style.map("Treeview", background=[("selected", c["select"])],
                  foreground=[("selected", c["fg"])])
        style.configure("Treeview.Heading", background=c["header"],
                        foreground=c["fg"], relief="flat",
                        bordercolor=c["border"])
        style.map("Treeview.Heading", background=[("active", c["hover"])])

        style.configure("TScrollbar", background=c["button"], troughcolor=c["bg"],
                        arrowcolor=c["fg"], bordercolor=c["bg"])

        style.configure("TNotebook", background=c["bg"], bordercolor=c["border"])
        style.configure("TNotebook.Tab", background=c["button"],
                        foreground=c["fg"], padding=(16, 6),
                        bordercolor=c["border"])
        style.map("TNotebook.Tab",
                  background=[("selected", c["bg"]), ("active", c["hover"])],
                  foreground=[("selected", c["fg"])])

        # The drop-down lists of the comboboxes are separate classic widgets
        for box in self.comboboxes:
            try:
                popdown = self.root.tk.call("ttk::combobox::PopdownWindow", str(box))
                self.root.tk.call(f"{popdown}.f.l", "configure",
                                  "-background", c["field"],
                                  "-foreground", c["fg"],
                                  "-selectbackground", c["select"],
                                  "-selectforeground", c["fg"])
            except tk.TclError:
                pass

        self.chart.configure(background=c["field"])
        self.theme_button.config(
            text="Switch to light mode" if self.dark else "Switch to dark mode")
        self.draw_chart()

    def toggle_theme(self):
        self.dark = not self.dark
        self.settings["dark_mode"] = self.dark
        save_settings(self.settings)
        self.apply_theme()

    # ---------- Refreshing what is on screen ----------

    def refresh(self):
        """Reload the table, the totals and the summary from the database."""
        # Keep the filter dropdown in sync with the categories in the database
        self.filter_category_box["values"] = ["All"] + database.get_categories()

        for item in self.tree.get_children():
            self.tree.delete(item)

        rows = database.get_expenses(self.active_category, self.active_month)
        for exp_id, exp_date, category, description, amount in rows:
            self.tree.insert("", "end", iid=str(exp_id),
                             values=(exp_id, exp_date, category,
                                     description, f"{amount:,.2f}"))

        total = database.get_total(self.active_category, self.active_month)
        filtered = self.active_category or self.active_month
        label = "Total (filtered)" if filtered else "Total"
        self.total_label.config(text=f"{label}: {total:,.2f}")

        # The summary table and chart are rebuilt every time, so they
        # always match the database
        self.refresh_summary()

    def refresh_summary(self):
        months = database.get_months()
        options = ["All time"] + months
        self.period_box["values"] = options
        if self.period_var.get() not in options:
            # First start, or the chosen month no longer has any expenses
            self.period_var.set(months[0] if months else "All time")

        period = self.period_var.get()
        month = None if period == "All time" else period
        self.summary_rows = database.get_category_summary(month)

        grand_total = sum(row[2] for row in self.summary_rows)
        count = sum(row[1] for row in self.summary_rows)

        for item in self.summary_tree.get_children():
            self.summary_tree.delete(item)
        for category, number, total in self.summary_rows:
            share = total / grand_total * 100 if grand_total else 0
            self.summary_tree.insert("", "end", values=(
                category, number, f"{total:,.2f}", f"{share:.1f}%"))

        self.summary_total_label.config(
            text=f"Total: {grand_total:,.2f}  ({count} expenses)")
        self.draw_chart()

    def draw_chart(self):
        """Draw the bar chart of spending per category."""
        c = DARK if self.dark else LIGHT
        canvas = self.chart
        canvas.delete("all")  # wipe the old drawing, then draw it again

        width = canvas.winfo_width()
        height = canvas.winfo_height()
        if width < 100 or height < 100:
            return  # the window is not on screen yet

        period = self.period_var.get() or "All time"
        canvas.create_text(width / 2, 18, fill=c["fg"],
                           text=f"Spending by category - {period}",
                           font=("Segoe UI", 11, "bold"))

        if not self.summary_rows:
            canvas.create_text(width / 2, height / 2, fill=c["muted"],
                               text="No expenses for this period",
                               font=("Segoe UI", 11))
            return

        left, right, top, bottom = 70, 20, 55, height - 45
        plot_height = bottom - top
        axis_max = nice_max(max(row[2] for row in self.summary_rows))

        # Grid lines with the amounts on the left
        for i in range(5):
            value = axis_max * i / 4
            y = bottom - plot_height * i / 4
            canvas.create_line(left, y, width - right, y, fill=c["grid"])
            canvas.create_text(left - 8, y, text=format_axis(value),
                               fill=c["muted"], anchor="e",
                               font=("Segoe UI", 9))

        # One bar per category
        slot = (width - left - right) / len(self.summary_rows)
        bar_width = min(slot * 0.6, 90)
        for index, (category, number, total) in enumerate(self.summary_rows):
            center = left + slot * index + slot / 2
            bar_top = bottom - plot_height * total / axis_max
            color = CHART_COLORS[index % len(CHART_COLORS)]
            canvas.create_rectangle(center - bar_width / 2, bar_top,
                                    center + bar_width / 2, bottom,
                                    fill=color, outline="")
            canvas.create_text(center, bar_top - 6, text=f"{total:,.2f}",
                               fill=c["fg"], anchor="s", font=("Segoe UI", 9))
            canvas.create_text(center, bottom + 8, text=category,
                               fill=c["fg"], anchor="n", width=slot - 6,
                               justify="center", font=("Segoe UI", 9))

    # ---------- Helpers ----------

    def read_form(self):
        """Check the form. Return (date, category, description, amount) or None."""
        date_text = self.date_var.get().strip()
        category = self.category_var.get().strip()
        description = self.description_var.get().strip()
        amount_text = self.amount_var.get().strip().replace(",", "")

        try:
            datetime.strptime(date_text, "%Y-%m-%d")
        except ValueError:
            messagebox.showerror("Invalid date", "Use the format YYYY-MM-DD, e.g. 2026-11-21.")
            return None

        if not category:
            messagebox.showerror("Missing category", "Please choose or type a category.")
            return None

        try:
            amount = float(amount_text)
        except ValueError:
            messagebox.showerror("Invalid amount", "Amount must be a number, e.g. 12.50.")
            return None
        if amount <= 0:
            messagebox.showerror("Invalid amount", "Amount must be greater than zero.")
            return None

        return date_text, category, description, amount

    def clear_form(self):
        self.selected_id = None
        self.date_var.set(date.today().isoformat())
        self.category_var.set("")
        self.description_var.set("")
        self.amount_var.set("")
        self.tree.selection_remove(self.tree.selection())

    # ---------- Button and click handlers ----------

    def apply_filter(self):
        category = self.filter_category_var.get()
        month = self.filter_month_var.get().strip()

        if month:
            try:
                parsed = datetime.strptime(month, "%Y-%m")
            except ValueError:
                messagebox.showerror("Invalid month", "Use the format YYYY-MM, e.g. 2026-11.")
                return
            month = parsed.strftime("%Y-%m")  # turns 2026-1 into 2026-01
            self.filter_month_var.set(month)

        self.active_category = None if category == "All" else category
        self.active_month = month or None
        self.clear_form()
        self.refresh()

    def reset_filter(self):
        self.filter_category_var.set("All")
        self.filter_month_var.set("")
        self.active_category = None
        self.active_month = None
        self.clear_form()
        self.refresh()

    def on_export(self):
        # Export exactly what the filters currently select
        rows = database.get_expenses(self.active_category, self.active_month)
        if not rows:
            messagebox.showinfo("Nothing to export", "There are no expenses to export.")
            return

        filepath = filedialog.asksaveasfilename(
            title="Save Excel report",
            defaultextension=".xlsx",
            filetypes=[("Excel workbook", "*.xlsx")],
            initialfile=f"expenses_{date.today().isoformat()}.xlsx",
        )
        if not filepath:
            return  # the user cancelled

        try:
            excel_export.export_to_excel(rows, filepath)
        except PermissionError:
            messagebox.showerror(
                "Could not save",
                "The file may be open in Excel. Close it and try again.")
            return

        messagebox.showinfo("Exported", f"Saved {len(rows)} expenses to:\n{filepath}")

    def on_add(self):
        data = self.read_form()
        if data is None:
            return
        database.add_expense(*data)
        self.clear_form()
        self.refresh()

    def on_select(self, event):
        selection = self.tree.selection()
        if not selection:
            return
        values = [str(v) for v in self.tree.item(selection[0])["values"]]
        self.selected_id = int(selection[0])
        self.date_var.set(values[1])
        self.category_var.set(values[2])
        self.description_var.set(values[3])
        self.amount_var.set(values[4])

    def on_update(self):
        if self.selected_id is None:
            messagebox.showinfo("Select an expense", "Click an expense in the table first.")
            return
        data = self.read_form()
        if data is None:
            return
        database.update_expense(self.selected_id, *data)
        self.clear_form()
        self.refresh()

    def on_delete(self):
        if self.selected_id is None:
            messagebox.showinfo("Select an expense", "Click an expense in the table first.")
            return
        if messagebox.askyesno("Delete expense", "Delete the selected expense?"):
            database.delete_expense(self.selected_id)
            self.clear_form()
            self.refresh()


def main():
    database.create_table()
    root = tk.Tk()
    ExpenseApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()