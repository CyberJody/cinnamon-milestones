#!/usr/bin/python3
"""Tracker list and inline editor for the Milestones settings window.

Cinnamon's settings window loads this through the "custom" settings type.
It edits the "trackers" setting (a list of rows) in place: select a tracker
in the table and change it with the controls underneath. Every change is
saved straight away, so the desklet updates as you go.
"""

import calendar
import copy
import datetime
import gettext
import os
import subprocess

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gdk, Gio, Gtk, Pango
from xapp.SettingsWidgets import SettingsWidget

UUID = "milestones@CyberJody"
KEY = "trackers"

gettext.bindtextdomain(UUID, os.path.expanduser("~/.local/share/locale"))


def _(text):
    return gettext.dgettext(UUID, text)


MONTHS = [calendar.month_name[m] for m in range(1, 13)]
MONTHS_SHORT = [calendar.month_abbr[m] for m in range(1, 13)]
CLOCKS = [("am", "AM"), ("pm", "PM"), ("24h", "24H")]

DAY_WIDTH, DAY_HEIGHT = 34, 28

# Sizes only. Colors always come from the GTK theme.
CSS = (".milestones-day { padding: 0; margin: 1px; min-width: %dpx; min-height: %dpx; }"
       % (DAY_WIDTH, DAY_HEIGHT)).encode()

COL_SHOW, COL_TITLE, COL_DATE, COL_TIME, COL_MONTHLY, COL_YEARLY = range(6)


# ---- tracker rows -------------------------------------------------------

def to_int(value, default, low, high):
    try:
        number = int(value)
    except (TypeError, ValueError):
        return default
    return number if low <= number <= high else default


def normalize(row):
    """Returns a tracker row with every field present and well-typed."""
    row = dict(row or {})
    hour = row.get("hour")
    return {
        "enabled": row.get("enabled") is not False,
        "title": str(row.get("title") or ""),
        "month": to_int(row.get("month"), 1, 1, 12),
        "day": to_int(row.get("day"), 1, 1, 31),
        "year": str(row.get("year") or "").strip(),
        "hour": str("" if hour is None else hour).strip(),
        "minute": to_int(row.get("minute"), 0, 0, 59),
        "clock": row.get("clock") if row.get("clock") in ("am", "pm", "24h") else "24h",
        "monthly": bool(row.get("monthly")),
        "yearly": bool(row.get("yearly")),
    }


def new_row():
    """A new tracker: today at midnight, with the year left to fill in."""
    today = datetime.date.today()
    return normalize({"month": today.month, "day": today.day,
                      "hour": "12", "clock": "am"})


def is_digits(text):
    return text.isascii() and text.isdigit()


def parse_year(text):
    """Year text -> the year, None when blank, or -1 when it isn't a year."""
    text = (text or "").strip()
    if not text:
        return None
    if len(text) == 4 and is_digits(text) and int(text) >= 1:
        return int(text)
    return -1


def hour24(text, clock):
    """Hour text + AM/PM/24H -> 0-23. Blank is midnight. None if invalid."""
    text = (text or "").strip()
    if not text:
        return 0
    if not is_digits(text) or len(text) > 2:
        return None
    hour = int(text)
    if clock == "24h":
        return hour if hour <= 23 else None
    if not 1 <= hour <= 12:
        return None
    return hour % 12 + (12 if clock == "pm" else 0)


def parse_minute(text):
    """Minute text -> 0-59. Blank is 0. None if invalid."""
    text = (text or "").strip()
    if not text:
        return 0
    if not is_digits(text) or int(text) > 59:
        return None
    return int(text)


def has_real_year(row):
    """True when the tracker counts to one exact date in a known year."""
    year = parse_year(row["year"])
    return not row["monthly"] and not row["yearly"] and year is not None and year > 0


def month_days(row):
    """How many days the calendar offers for this tracker."""
    if row["monthly"]:
        return 31
    if has_real_year(row):
        return calendar.monthrange(parse_year(row["year"]), row["month"])[1]
    return calendar.monthrange(2024, row["month"])[1]      # leap year: Feb 29


def time_label(row):
    hour = hour24(row["hour"], row["clock"])
    if hour is None:
        return "%s:%02d" % (row["hour"], row["minute"])
    if row["clock"] == "24h":
        return "%d:%02d" % (hour, row["minute"])
    return "%d:%02d %s" % (hour % 12 or 12, row["minute"], "PM" if hour >= 12 else "AM")


def date_label(row):
    if row["monthly"]:
        return _("Day %d") % row["day"]
    text = "%s %d" % (MONTHS_SHORT[row["month"] - 1], row["day"])
    if row["yearly"] or not row["year"]:
        return text
    return "%s, %s" % (text, row["year"])


def problem(row, minute_text=None):
    """Why this tracker can't count yet, as a sentence. None when it can."""
    if hour24(row["hour"], row["clock"]) is None:
        if row["clock"] == "24h":
            return _("Hour must be 0–23 with 24H.")
        return _("Hour must be 1–12 with AM or PM.")
    if minute_text is not None and parse_minute(minute_text) is None:
        return _("Minutes must be 0–59.")
    if not row["monthly"] and not row["yearly"]:
        year = parse_year(row["year"])
        if year is None:
            return _("Enter a year, or tick Monthly or Yearly.")
        if year < 0:
            return _("Year needs 4 digits.")
    if row["day"] > month_days(row):
        return _("%(month)s has no day %(day)d. Pick a day.") % {
            "month": MONTHS[row["month"] - 1], "day": row["day"]}
    return None


def summary(row):
    """Plain-language description of what a valid tracker counts to."""
    values = {"month": MONTHS[row["month"] - 1], "day": row["day"],
              "time": time_label(row)}
    if row["monthly"]:
        text = _("Every month on day %(day)d at %(time)s.") % values
        if row["day"] > 28:
            text += " " + _("Shorter months use their last day.")
    elif row["yearly"]:
        text = _("Every year on %(month)s %(day)d at %(time)s.") % values
        if row["month"] == 2 and row["day"] == 29:
            text += " " + _("February 28 in non-leap years.")
    else:
        year = parse_year(row["year"])
        values["year"] = year
        values["weekday"] = calendar.day_name[calendar.weekday(year, row["month"], row["day"])]
        text = _("%(weekday)s, %(month)s %(day)d, %(year)d at %(time)s.") % values
    if not row["hour"]:
        text += " " + _("Hour is blank, so midnight is used.")
    return text


def week_start():
    """First day of the week as 0 = Monday … 6 = Sunday, following Cinnamon."""
    schema = "org.cinnamon.desktop.interface"
    if Gio.SettingsSchemaSource.get_default().lookup(schema, True):
        setting = Gio.Settings.new(schema).get_int("first-day-of-week")
        if 0 <= setting <= 6:               # 0 = Sunday; 7 = locale default
            return (setting - 1) % 7
    try:
        out = subprocess.run(["locale", "first_weekday", "week-1stday"],
                             capture_output=True, text=True, timeout=2).stdout.split()
        origin = datetime.datetime.strptime(out[1], "%Y%m%d").weekday()
        return (origin + int(out[0]) - 1) % 7
    except (OSError, ValueError, IndexError, subprocess.SubprocessError):
        return 6


def icon_name(name):
    """Cinnamon 6.6 ships xsi-* symbolic icons; older versions don't."""
    xsi = "xsi-" + name
    return xsi if Gtk.IconTheme.get_default().has_icon(xsi) else name


class DigitsEntry(Gtk.Entry, Gtk.Editable):
    """A short text box that only accepts digits.

    Gtk.Editable has to be listed as a base: without it the override below
    lands on Gtk.Entry itself and every text box in the window turns
    digits-only.
    """

    def __init__(self, length, placeholder=""):
        Gtk.Entry.__init__(self)
        self.set_max_length(length)
        self.set_width_chars(length + 1)
        self.set_max_width_chars(length + 1)
        self.set_placeholder_text(placeholder)
        self.set_input_purpose(Gtk.InputPurpose.DIGITS)

    def do_insert_text(self, text, length, position):
        # Typed letters are ignored; a pasted "2026 " keeps its digits.
        digits = "".join(ch for ch in text if is_digits(ch))
        if not digits:
            return position
        return position + self.get_buffer().insert_text(position, digits, len(digits))


# ---- the widget ---------------------------------------------------------

class TrackerEditor(SettingsWidget):
    def __init__(self, info, key, settings):
        SettingsWidget.__init__(self)
        self.fill_row()
        self.set_orientation(Gtk.Orientation.VERTICAL)
        self.set_spacing(0)

        self.settings = settings
        self.rows = []
        self._loading = False       # filling widgets, not a user edit
        self._saving = False        # our own write, not an outside change
        self._calendar_layout_shown = None
        self._day_buttons = {}
        self._years = {}            # year a tracker had before it repeated
        self._week_start = week_start()

        provider = Gtk.CssProvider()
        provider.load_from_data(CSS)
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        self._build_table()
        self._build_toolbar()
        self.pack_start(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL), False, False, 0)
        self._build_editor()

        self.settings.listen(KEY, self._on_outside_change)
        self._reload(select=0)

    # ---- construction ----

    def _build_table(self):
        self.store = Gtk.ListStore(bool, str, str, str, bool, bool)
        self.tree = Gtk.TreeView(model=self.store)

        def toggle_column(title, column, field):
            renderer = Gtk.CellRendererToggle()
            renderer.connect("toggled", self._on_cell_toggled, field)
            self.tree.append_column(Gtk.TreeViewColumn(title, renderer, active=column))

        def text_column(title, column, expand=False):
            renderer = Gtk.CellRendererText()
            renderer.set_property("xpad", 6)
            if expand:
                renderer.set_property("ellipsize", Pango.EllipsizeMode.END)
            view_column = Gtk.TreeViewColumn(title, renderer, text=column)
            view_column.set_expand(expand)
            self.tree.append_column(view_column)

        toggle_column(_("Show"), COL_SHOW, "enabled")
        text_column(_("Title"), COL_TITLE, expand=True)
        text_column(_("Date"), COL_DATE)
        text_column(_("Time"), COL_TIME)
        toggle_column(_("Monthly"), COL_MONTHLY, "monthly")
        toggle_column(_("Yearly"), COL_YEARLY, "yearly")

        self.tree.get_selection().connect("changed", self._on_selection_changed)
        self.tree.connect("row-activated", lambda *args: self.title_entry.grab_focus())

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_size_request(-1, 112)
        scrolled.add(self.tree)
        self.pack_start(scrolled, True, True, 0)

    def _build_toolbar(self):
        toolbar = Gtk.Toolbar()
        toolbar.set_icon_size(Gtk.IconSize.MENU)
        toolbar.get_style_context().add_class("inline-toolbar")

        def button(icon, tooltip, callback, *args):
            tool = Gtk.ToolButton()
            tool.set_icon_name(icon_name(icon))
            tool.set_tooltip_text(tooltip)
            tool.connect("clicked", callback, *args)
            toolbar.insert(tool, -1)
            return tool

        button("list-add-symbolic", _("Add a tracker"), self._on_add)
        self.remove_button = button("list-remove-symbolic", _("Remove the selected tracker"), self._on_remove)
        self.up_button = button("go-up-symbolic", _("Move up"), self._on_move, -1)
        self.down_button = button("go-down-symbolic", _("Move down"), self._on_move, 1)
        self.pack_start(toolbar, False, False, 0)

    def _build_editor(self):
        editor = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=24)
        editor.set_border_width(14)
        self.pack_start(editor, False, False, 0)

        form = Gtk.Grid(column_spacing=12, row_spacing=8)
        form.set_hexpand(True)
        editor.pack_start(form, True, True, 0)
        self.form = form

        def label(text, row):
            widget = Gtk.Label(label=text, xalign=0)
            widget.get_style_context().add_class("dim-label")
            form.attach(widget, 0, row, 1, 1)

        label(_("Title"), 0)
        self.title_entry = Gtk.Entry(hexpand=True)
        self.title_entry.set_placeholder_text(_("What are you tracking?"))
        self.title_entry.connect("changed", self._on_title_changed)
        form.attach(self.title_entry, 1, 0, 1, 1)

        label(_("Date"), 1)
        date_box = Gtk.Box(spacing=8)
        self.month_combo = Gtk.ComboBoxText()
        for name in MONTHS:
            self.month_combo.append_text(name)
        self.month_combo.connect("changed", self._on_month_changed)
        self.year_entry = DigitsEntry(4, _("Year"))
        self.year_entry.set_no_show_all(True)
        self.year_entry.connect("changed", self._on_year_changed)
        date_box.pack_start(self.month_combo, False, False, 0)
        date_box.pack_start(self.year_entry, False, False, 0)
        form.attach(date_box, 1, 1, 1, 1)

        label(_("Time"), 2)
        time_box = Gtk.Box(spacing=6)
        self.hour_entry = DigitsEntry(2)
        self.hour_entry.connect("changed", self._on_hour_changed)
        self.minute_entry = DigitsEntry(2)
        self.minute_entry.connect("changed", self._on_minute_changed)
        self.minute_entry.connect("focus-out-event", self._on_minute_focus_out)
        self.clock_combo = Gtk.ComboBoxText()
        for clock_id, text in CLOCKS:
            self.clock_combo.append(clock_id, text)
        self.clock_combo.connect("changed", self._on_clock_changed)
        time_box.pack_start(self.hour_entry, False, False, 0)
        time_box.pack_start(Gtk.Label(label=":"), False, False, 0)
        time_box.pack_start(self.minute_entry, False, False, 0)
        time_box.pack_start(self.clock_combo, False, False, 6)
        form.attach(time_box, 1, 2, 1, 1)

        label(_("Repeat"), 3)
        repeat_box = Gtk.Box(spacing=18)
        self.monthly_check = Gtk.CheckButton(label=_("Monthly"))
        self.yearly_check = Gtk.CheckButton(label=_("Yearly"))
        self.monthly_check.connect("toggled", self._on_repeat_toggled, "monthly")
        self.yearly_check.connect("toggled", self._on_repeat_toggled, "yearly")
        repeat_box.pack_start(self.monthly_check, False, False, 0)
        repeat_box.pack_start(self.yearly_check, False, False, 0)
        form.attach(repeat_box, 1, 3, 1, 1)

        status_box = Gtk.Box(spacing=6)
        status_box.set_vexpand(True)
        status_box.set_valign(Gtk.Align.START)
        self.status_icon = Gtk.Image.new_from_icon_name(
            icon_name("dialog-warning-symbolic"), Gtk.IconSize.MENU)
        self.status_icon.set_valign(Gtk.Align.START)
        self.status_icon.set_no_show_all(True)
        self.status = Gtk.Label(xalign=0, yalign=0, wrap=True, max_width_chars=40)
        status_box.pack_start(self.status_icon, False, False, 0)
        status_box.pack_start(self.status, True, True, 0)
        form.attach(status_box, 0, 4, 2, 1)

        calendar_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        calendar_box.set_size_request(7 * (DAY_WIDTH + 2), -1)
        calendar_box.set_valign(Gtk.Align.START)
        self.calendar_caption = Gtk.Label(xalign=0.5)
        bold = Pango.AttrList()
        bold.insert(Pango.attr_weight_new(Pango.Weight.BOLD))
        self.calendar_caption.set_attributes(bold)
        # Equal-height rows, always seven of them (weekday names + six
        # weeks), so the window keeps its height from month to month. The
        # gaps are margins on the day buttons: grid spacing would vanish
        # around an empty week and change the height.
        self.calendar_grid = Gtk.Grid(row_homogeneous=True)
        self.calendar_grid.set_halign(Gtk.Align.CENTER)
        self.calendar_grid.set_valign(Gtk.Align.START)
        calendar_box.pack_start(self.calendar_caption, False, False, 0)
        calendar_box.pack_start(self.calendar_grid, False, False, 0)
        editor.pack_end(calendar_box, False, False, 0)
        self.calendar_box = calendar_box

    # ---- saving and loading ----

    def _commit(self):
        """Saves the list; the settings window then tells the desklet."""
        self._saving = True
        try:
            self.settings.set_value(KEY, copy.deepcopy(self.rows))
        finally:
            self._saving = False

    def _on_outside_change(self, *args):
        # Import, Reset to defaults, or the desklet's own Restore button.
        if not self._saving:
            self._reload(select=self._selected())

    def _reload(self, select=None):
        self.rows = [normalize(row) for row in (self.settings.get_value(KEY) or [])]
        self._years = {}
        self._loading = True
        self.store.clear()
        for row in self.rows:
            self.store.append(self._store_values(row))
        self._loading = False
        self._select(select)
        self._load_editor()

    def _store_values(self, row):
        return [row["enabled"], row["title"] or _("(no title)"), date_label(row),
                time_label(row), row["monthly"], row["yearly"]]

    def _refresh_table_row(self, index):
        tree_iter = self.store.get_iter(Gtk.TreePath(index))
        for column, value in enumerate(self._store_values(self.rows[index])):
            self.store.set_value(tree_iter, column, value)

    def _selected(self):
        model, tree_iter = self.tree.get_selection().get_selected()
        return model.get_path(tree_iter).get_indices()[0] if tree_iter else None

    def _select(self, index):
        if not self.rows:
            return
        index = min(max(index or 0, 0), len(self.rows) - 1)
        self.tree.get_selection().select_path(Gtk.TreePath(index))

    def _row(self):
        index = self._selected()
        return None if index is None else self.rows[index]

    # ---- showing the selected tracker ----

    def _load_editor(self):
        """Fills the controls from the selected tracker."""
        index = self._selected()
        row = self._row()
        self.remove_button.set_sensitive(row is not None)
        self.up_button.set_sensitive(row is not None and index > 0)
        self.down_button.set_sensitive(row is not None and index < len(self.rows) - 1)
        self.form.set_sensitive(row is not None)
        self.calendar_box.set_sensitive(row is not None)

        self._loading = True
        self.title_entry.set_text(row["title"] if row else "")
        self.month_combo.set_active(row["month"] - 1 if row else -1)
        self.year_entry.set_text(row["year"] if row else "")
        self.hour_entry.set_text(row["hour"] if row else "")
        self.minute_entry.set_text("%02d" % row["minute"] if row else "")
        self.clock_combo.set_active_id(row["clock"] if row else None)
        self.monthly_check.set_active(bool(row and row["monthly"]))
        self.yearly_check.set_active(bool(row and row["yearly"]))
        self._loading = False
        self._sync_editor()

    def _sync_editor(self):
        """Updates everything that depends on the tracker's current values."""
        row = self._row()
        if row is None:
            self._show_calendar(None)
            self._set_status(_("Click + to add a tracker."), False)
            return

        self.month_combo.set_sensitive(not row["monthly"])
        repeating = row["monthly"] or row["yearly"]
        self.year_entry.set_visible(not repeating)      # repeats have no year

        minute_text = self.minute_entry.get_text()
        self._mark(self.hour_entry, hour24(row["hour"], row["clock"]) is None)
        self._mark(self.minute_entry, parse_minute(minute_text) is None)
        self._mark(self.year_entry, not repeating and parse_year(row["year"]) == -1)

        self._show_calendar(row)
        trouble = problem(row, minute_text)
        self._set_status(trouble or summary(row), trouble is not None)

    @staticmethod
    def _mark(widget, wrong):
        context = widget.get_style_context()
        if wrong:
            context.add_class("error")
        else:
            context.remove_class("error")

    def _set_status(self, text, is_problem):
        self.status.set_text(text)
        self.status_icon.set_visible(is_problem)
        context = self.status.get_style_context()
        if is_problem:
            context.remove_class("dim-label")
        else:
            context.add_class("dim-label")

    def _calendar_layout(self, row):
        """Caption, number of days, blank cells before day 1, weekday names?"""
        if row is None:
            return ("", 31, 0, False)
        if row["monthly"]:
            return (_("Day of the month"), 31, 0, False)
        month = MONTHS[row["month"] - 1]
        if has_real_year(row):
            year = parse_year(row["year"])
            first_weekday, days = calendar.monthrange(year, row["month"])
            return ("%s %d" % (month, year), days, (first_weekday - self._week_start) % 7, True)
        return (month, month_days(row), 0, False)

    def _show_calendar(self, row):
        """Draws the day picker for the tracker's month and marks its day."""
        layout = self._calendar_layout(row)
        self._loading = True
        if layout != self._calendar_layout_shown:
            self._calendar_layout_shown = layout
            self._rebuild_calendar(*layout)
        # A day the month doesn't have selects the hidden button: none shown.
        day = row["day"] if row else None
        self._day_buttons.get(day, self._no_day).set_active(True)
        self._loading = False

    def _rebuild_calendar(self, caption, days, offset, weekdays):
        for child in self.calendar_grid.get_children():
            self.calendar_grid.remove(child)
        self._day_buttons = {}
        self._no_day = Gtk.RadioButton()
        self.calendar_caption.set_text(caption)
        self.calendar_grid.attach(Gtk.Label(), 0, 6, 1, 1)     # seventh row

        top = 0
        if weekdays:
            for column in range(7):
                name = calendar.day_abbr[(self._week_start + column) % 7][:2]
                header = Gtk.Label(label=name)
                header.get_style_context().add_class("dim-label")
                self.calendar_grid.attach(header, column, 0, 1, 1)
            top = 1

        for day in range(1, days + 1):
            button = Gtk.RadioButton.new_with_label_from_widget(self._no_day, str(day))
            button.set_mode(False)
            button.set_relief(Gtk.ReliefStyle.NONE)
            button.get_style_context().add_class("milestones-day")
            button.connect("toggled", self._on_day_toggled, day)
            cell = offset + day - 1
            self.calendar_grid.attach(button, cell % 7, top + cell // 7, 1, 1)
            self._day_buttons[day] = button
        self.calendar_grid.show_all()

    # ---- edits ----

    def _changed(self, clamp_day=False):
        """Call after changing the selected tracker: redraw and save."""
        row = self._row()
        if clamp_day:
            row["day"] = min(row["day"], month_days(row))
        self._sync_editor()
        self._refresh_table_row(self._selected())
        self._commit()

    def _on_selection_changed(self, selection):
        if not self._loading:
            self._load_editor()

    def _on_title_changed(self, entry):
        if not self._loading:
            self._row()["title"] = entry.get_text()
            self._changed()

    def _on_month_changed(self, combo):
        if not self._loading and combo.get_active() >= 0:
            self._row()["month"] = combo.get_active() + 1
            self._changed(clamp_day=True)

    def _on_year_changed(self, entry):
        if not self._loading:
            self._row()["year"] = entry.get_text()
            self._changed(clamp_day=True)

    def _on_hour_changed(self, entry):
        if not self._loading:
            self._row()["hour"] = entry.get_text()
            self._changed()

    def _on_minute_changed(self, entry):
        if self._loading:
            return
        minute = parse_minute(entry.get_text())
        if minute is not None:          # keep the last good value otherwise
            self._row()["minute"] = minute
        self._changed()

    def _on_minute_focus_out(self, entry, event):
        row = self._row()
        if row is not None and parse_minute(entry.get_text()) is not None:
            self._loading = True
            entry.set_text("%02d" % row["minute"])
            self._loading = False
        return False

    def _on_clock_changed(self, combo):
        if self._loading or combo.get_active_id() is None:
            return
        row = self._row()
        old, new = row["clock"], combo.get_active_id()
        hour = hour24(row["hour"], old)
        if row["hour"] and hour is not None:
            # Switching between 12- and 24-hour keeps the same moment.
            if new == "24h":
                row["hour"] = str(hour)
            elif old == "24h":
                row["hour"] = str(hour % 12 or 12)
                new = "pm" if hour >= 12 else "am"
        row["clock"] = new
        self._loading = True
        self.hour_entry.set_text(row["hour"])
        combo.set_active_id(new)
        self._loading = False
        self._changed()

    def _set_repeat(self, row, field, active):
        """Monthly and Yearly exclude each other, and neither uses a year."""
        row[field] = active
        if active:
            row["yearly" if field == "monthly" else "monthly"] = False
            if row["year"]:
                self._years[id(row)] = row["year"]
            row["year"] = ""
        elif not row["year"]:
            # Unticking brings back the year the tracker had before.
            row["year"] = self._years.pop(id(row), "")
        # Day 31 of a monthly tracker may not exist once it has a month.
        row["day"] = min(row["day"], month_days(row))

    def _on_repeat_toggled(self, check, field):
        if self._loading:
            return
        self._set_repeat(self._row(), field, check.get_active())
        self._load_editor()
        self._refresh_table_row(self._selected())
        self._commit()

    def _on_day_toggled(self, button, day):
        # The theme's accent marks the chosen day; a flat checked button
        # alone is invisible in some themes.
        context = button.get_style_context()
        if button.get_active():
            context.add_class("suggested-action")
        else:
            context.remove_class("suggested-action")
        if not self._loading and button.get_active():
            self._row()["day"] = day
            self._changed()

    def _on_cell_toggled(self, renderer, path, field):
        index = Gtk.TreePath(path).get_indices()[0]
        row = self.rows[index]
        if field == "enabled":
            row["enabled"] = not row["enabled"]
        else:
            self._set_repeat(row, field, not row[field])
        self._refresh_table_row(index)
        if index == self._selected():
            self._load_editor()
        self._commit()

    def _on_add(self, *args):
        self.rows.append(new_row())
        self.store.append(self._store_values(self.rows[-1]))
        self._select(len(self.rows) - 1)
        self._commit()
        self.title_entry.grab_focus()

    def _on_remove(self, *args):
        index = self._selected()
        if index is None:
            return
        self._years.pop(id(self.rows[index]), None)
        del self.rows[index]
        self._loading = True
        self.store.remove(self.store.get_iter(Gtk.TreePath(index)))
        self._loading = False
        self._select(index)
        self._load_editor()
        self._commit()

    def _on_move(self, button, step):
        index = self._selected()
        target = None if index is None else index + step
        if target is None or not 0 <= target < len(self.rows):
            return
        self.rows[index], self.rows[target] = self.rows[target], self.rows[index]
        self._refresh_table_row(index)
        self._refresh_table_row(target)
        self._select(target)
        self._load_editor()
        self._commit()
