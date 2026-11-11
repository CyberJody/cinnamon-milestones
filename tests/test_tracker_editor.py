#!/usr/bin/python3
"""Drives the tracker editor without showing a window.

Run with the system Python (it needs PyGObject and xapp):
    /usr/bin/python3 tests/test_tracker_editor.py
"""

import copy
import importlib.util
import os
import sys

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

HERE = os.path.dirname(os.path.abspath(__file__))
SPICE = os.path.join(HERE, "..", "time-since@CyberJody", "files", "time-since@CyberJody")
spec = importlib.util.spec_from_file_location("TrackerEditor", os.path.join(SPICE, "TrackerEditor.py"))
te = importlib.util.module_from_spec(spec)
spec.loader.exec_module(te)

failures = []


def check(name, got, want):
    if got != want:
        failures.append(name)
        print("FAIL %s\n     got  %r\n     want %r" % (name, got, want))
    else:
        print("ok   %s" % name)


class FakeSettings:
    """Stands in for Cinnamon's JSONSettingsHandler."""

    def __init__(self, rows):
        self.value = rows
        self.saves = 0
        self.listeners = []

    def get_value(self, key):
        return copy.deepcopy(self.value)

    def set_value(self, key, value):
        if value != self.value:
            self.value = copy.deepcopy(value)
            self.saves += 1

    def listen(self, key, callback):
        self.listeners.append(callback)

    def outside_change(self, rows):
        self.value = rows
        for callback in self.listeners:
            callback("trackers", rows)


def pump():
    while Gtk.events_pending():
        Gtk.main_iteration()


def build(rows):
    settings = FakeSettings(rows)
    widget = te.TrackerEditor({}, "trackers-editor", settings)
    window = Gtk.OffscreenWindow()
    window.add(widget)
    window.show_all()
    pump()
    return settings, widget, window


def row(**fields):
    base = {"enabled": True, "title": "T", "month": 11, "day": 10, "year": "2026",
            "hour": "9", "minute": 30, "clock": "pm", "monthly": False, "yearly": False}
    base.update(fields)
    return base


# ---- pure functions ----

check("hour24 9 pm", te.hour24("9", "pm"), 21)
check("hour24 12 am", te.hour24("12", "am"), 0)
check("hour24 12 pm", te.hour24("12", "pm"), 12)
check("hour24 blank", te.hour24("", "am"), 0)
check("hour24 23 24h", te.hour24("23", "24h"), 23)
check("hour24 0 24h", te.hour24("0", "24h"), 0)
check("hour24 24 24h", te.hour24("24", "24h"), None)
check("hour24 13 pm", te.hour24("13", "pm"), None)
check("hour24 0 am", te.hour24("0", "am"), None)
check("hour24 letters", te.hour24("ten", "am"), None)
check("parse_year blank", te.parse_year(""), None)
check("parse_year 2026", te.parse_year("2026"), 2026)
check("parse_year 26", te.parse_year("26"), -1)
check("parse_year 0000", te.parse_year("0000"), -1)
check("parse_minute blank", te.parse_minute(""), 0)
check("parse_minute 59", te.parse_minute("59"), 59)
check("parse_minute 60", te.parse_minute("60"), None)
check("days Feb 2026", te.month_days(row(month=2, year="2026")), 28)
check("days Feb 2028", te.month_days(row(month=2, year="2028")), 29)
check("days Feb yearly", te.month_days(row(month=2, year="", yearly=True)), 29)
check("days Feb blank year", te.month_days(row(month=2, year="")), 29)
check("days monthly", te.month_days(row(month=2, monthly=True)), 31)
check("days Apr", te.month_days(row(month=4)), 30)
check("normalize junk", te.normalize({"month": 99, "day": "x", "hour": 9, "minute": 75, "clock": "?"}),
      {"enabled": True, "title": "", "month": 1, "day": 1, "year": "", "hour": "9",
       "minute": 0, "clock": "24h", "monthly": False, "yearly": False})
check("problem none", te.problem(row()), None)
check("problem no year", te.problem(row(year="")), "Enter a year, or tick Monthly or Yearly.")
check("problem short year", te.problem(row(year="26")), "Year needs 4 digits.")
check("problem hour pm", te.problem(row(hour="13")), "Hour must be 1–12 with AM or PM.")
check("problem hour 24h", te.problem(row(hour="24", clock="24h")), "Hour must be 0–23 with 24H.")
check("problem minute", te.problem(row(), "75"), "Minutes must be 0–59.")
check("problem bad day", te.problem(row(month=2, day=31)), "February has no day 31. Pick a day.")
check("summary one-off", te.summary(row()), "Tuesday, November 10, 2026 at 9:30 PM.")
check("summary yearly", te.summary(row(month=3, day=14, year="", yearly=True, hour="12", clock="am", minute=0)),
      "Every year on March 14 at 12:00 AM.")
check("summary leap day", te.summary(row(month=2, day=29, year="", yearly=True)),
      "Every year on February 29 at 9:30 PM. February 28 in non-leap years.")
check("summary monthly 31", te.summary(row(day=31, monthly=True, year="")),
      "Every month on day 31 at 9:30 PM. Shorter months use their last day.")
check("summary 24h", te.summary(row(hour="21", clock="24h")), "Tuesday, November 10, 2026 at 21:30.")
check("summary blank hour", te.summary(row(hour="")),
      "Tuesday, November 10, 2026 at 12:30 AM. Hour is blank, so midnight is used.")
check("date label one-off", te.date_label(row()), "Nov 10, 2026")
check("date label yearly", te.date_label(row(yearly=True, year="")), "Nov 10")
check("date label monthly", te.date_label(row(monthly=True, year="")), "Day 10")

# ---- the widget ----

start = [row(title="Fasting Progress"),
         row(title="Mr. Kitty's Birthday.", month=1, day=1, year="", hour="12", clock="am", minute=0, yearly=True)]
settings, w, window = build(copy.deepcopy(start))

plain = Gtk.Entry()
plain.set_text("letters stay")
check("other text boxes still take letters", plain.get_text(), "letters stay")

check("loads title", w.title_entry.get_text(), "Fasting Progress")
check("loads month", w.month_combo.get_active_text(), "November")
check("loads year", w.year_entry.get_text(), "2026")
check("loads hour", w.hour_entry.get_text(), "9")
check("loads minute", w.minute_entry.get_text(), "30")
check("loads clock", w.clock_combo.get_active_id(), "pm")
check("calendar has 30 days", len(w._day_buttons), 30)
check("calendar selects day 10", w._day_buttons[10].get_active(), True)
check("selected day is marked", w._day_buttons[10].get_style_context().has_class("suggested-action"), True)
check("calendar caption", w.calendar_caption.get_text(), "November 2026")
check("status", w.status.get_text(), "Tuesday, November 10, 2026 at 9:30 PM.")
check("no save on load", settings.saves, 0)
check("table row", list(w.store[0]), [True, "Fasting Progress", "Nov 10, 2026", "9:30 PM", False, False])

w.year_entry.set_text("20a26x")
check("year keeps only digits", w.year_entry.get_text(), "2026")
w.year_entry.set_text("abc")
check("year ignores letters", w.year_entry.get_text(), "")
w.year_entry.set_text("202620")
check("year stops at 4 digits", w.year_entry.get_text(), "2026")
w.hour_entry.set_text("")
w.hour_entry.insert_text("1e1", 0)
check("hour keeps only digits", w.hour_entry.get_text(), "11")
w.hour_entry.set_text("9")
check("edits so far saved a good row", settings.value[0]["year"] + " " + settings.value[0]["hour"], "2026 9")

w._day_buttons[25].set_active(True)
check("click day saves", settings.value[0]["day"], 25)
check("old day unmarked", w._day_buttons[10].get_style_context().has_class("suggested-action"), False)
check("table follows", w.store[0][te.COL_DATE], "Nov 25, 2026")

w._day_buttons[30].set_active(True)
w.month_combo.set_active(1)                      # February 2026
check("month change saves", settings.value[0]["month"], 2)
check("Feb 2026 has 28 days", len(w._day_buttons), 28)
check("day clamps to 28", settings.value[0]["day"], 28)
check("clamped day selected", w._day_buttons[28].get_active(), True)
w.year_entry.set_text("2028")
check("Feb 2028 has 29 days", len(w._day_buttons), 29)
check("weekday offset Feb 2028", w.calendar_grid.child_get_property(w._day_buttons[1], "left-attach"),
      (1 - w._week_start) % 7)                    # Feb 1 2028 is a Tuesday

w.year_entry.set_text("")
check("blank year is a problem", w.status.get_text(), "Enter a year, or tick Monthly or Yearly.")
check("warning icon shown", w.status_icon.get_visible(), True)
check("blank year saved as blank", settings.value[0]["year"], "")
w.year_entry.set_text("202")
check("short year flagged", w.year_entry.get_style_context().has_class("error"), True)
w.year_entry.set_text("2026")
check("year ok again", w.year_entry.get_style_context().has_class("error"), False)
check("warning icon hidden", w.status_icon.get_visible(), False)

w.hour_entry.set_text("13")
check("13 PM flagged", w.hour_entry.get_style_context().has_class("error"), True)
check("13 PM message", w.status.get_text(), "Hour must be 1–12 with AM or PM.")
w.hour_entry.set_text("9")
w.clock_combo.set_active_id("24h")
check("PM -> 24H converts hour", (settings.value[0]["hour"], settings.value[0]["clock"]), ("21", "24h"))
check("24H table time", w.store[0][te.COL_TIME], "21:30")
w.clock_combo.set_active_id("am")
check("24H -> AM keeps the moment", (settings.value[0]["hour"], settings.value[0]["clock"]), ("9", "pm"))
check("combo shows PM", w.clock_combo.get_active_id(), "pm")
w.clock_combo.set_active_id("am")
check("PM -> AM flips half", (settings.value[0]["hour"], settings.value[0]["clock"]), ("9", "am"))
w.clock_combo.set_active_id("pm")

w.minute_entry.set_text("75")
check("75 minutes not saved", settings.value[0]["minute"], 30)
check("75 minutes flagged", w.status.get_text(), "Minutes must be 0–59.")
w.minute_entry.set_text("5")
check("minute saves", settings.value[0]["minute"], 5)

check("year box shown for one-off", w.year_entry.get_visible(), True)
w.yearly_check.set_active(True)
check("yearly saves", (settings.value[0]["yearly"], settings.value[0]["year"]), (True, ""))
check("year box hidden for yearly", w.year_entry.get_visible(), False)
check("yearly calendar has no weekdays", w.calendar_caption.get_text(), "February")
check("yearly Feb offers 29", len(w._day_buttons), 29)
w.monthly_check.set_active(True)
check("monthly unticks yearly", (settings.value[0]["monthly"], settings.value[0]["yearly"]), (True, False))
check("yearly box follows", w.yearly_check.get_active(), False)
check("month off for monthly", w.month_combo.get_sensitive(), False)
check("monthly offers 31", len(w._day_buttons), 31)
check("monthly caption", w.calendar_caption.get_text(), "Day of the month")
w._day_buttons[31].set_active(True)
check("monthly 31 status", w.status.get_text(),
      "Every month on day 31 at 9:05 PM. Shorter months use their last day.")
w.monthly_check.set_active(False)
check("unticking brings the year back", settings.value[0]["year"], "2026")
check("year box shows it", (w.year_entry.get_visible(), w.year_entry.get_text()), (True, "2026"))
check("day clamps back to Feb 2026", settings.value[0]["day"], 28)
check("one-off counts again", w.status.get_text(), "Saturday, February 28, 2026 at 9:05 PM.")

w.title_entry.set_text("Renamed")
check("title saves", settings.value[0]["title"], "Renamed")
check("title in table", w.store[0][te.COL_TITLE], "Renamed")

w._on_cell_toggled(None, "1", "enabled")
check("Show toggle saves", settings.value[1]["enabled"], False)
w._on_cell_toggled(None, "1", "monthly")
check("table Monthly unticks Yearly", (settings.value[1]["monthly"], settings.value[1]["yearly"]), (True, False))
w._on_cell_toggled(None, "1", "yearly")
w._on_cell_toggled(None, "0", "yearly")
check("table Yearly tick clears year", settings.value[0]["year"], "")
w._on_cell_toggled(None, "0", "yearly")
check("table Yearly untick restores year", settings.value[0]["year"], "2026")
w._on_cell_toggled(None, "1", "yearly")
check("never-had-a-year stays blank", settings.value[1]["year"], "")
check("and asks for one", te.problem(settings.value[1]), "Enter a year, or tick Monthly or Yearly.")
w._on_cell_toggled(None, "1", "yearly")

w._on_add()
check("add appends", len(settings.value), 3)
check("new tracker selected", w._selected(), 2)
check("new tracker has blank year", settings.value[2]["year"], "")
check("new tracker asks for year", w.status.get_text(), "Enter a year, or tick Monthly or Yearly.")
w._on_move(None, -1)
check("move up", [r["title"] for r in settings.value], ["Renamed", "", "Mr. Kitty's Birthday."])
check("selection follows move", w._selected(), 1)
check("up enabled, down enabled", (w.up_button.get_sensitive(), w.down_button.get_sensitive()), (True, True))
w._on_remove()
check("remove", [r["title"] for r in settings.value], ["Renamed", "Mr. Kitty's Birthday."])
check("selection after remove", w._selected(), 1)
check("editor shows next tracker", w.title_entry.get_text(), "Mr. Kitty's Birthday.")
check("last row can't move down", w.down_button.get_sensitive(), False)

settings.outside_change([row(title="Restored", day=31, month=2)])
check("outside change reloads", w.title_entry.get_text(), "Restored")
check("bad stored day shows problem", w.status.get_text(), "February has no day 31. Pick a day.")
check("no day selected for bad date", any(b.get_active() for b in w._day_buttons.values()), False)

settings.outside_change([])
check("empty list disables form", w.form.get_sensitive(), False)
check("empty list hint", w.status.get_text(), "Click + to add a tracker.")
check("empty list greys the calendar", (w.calendar_box.get_sensitive(), w.calendar_caption.get_text()), (False, ""))
w._on_remove()
w._on_add()
check("add from empty", len(settings.value), 1)
check("form enabled again", w.form.get_sensitive(), True)

# The calendar keeps one height whether the month spans four weeks or six.
def last_week():
    return max(w.calendar_grid.child_get_property(b, "top-attach") for b in w._day_buttons.values())

settings.outside_change([row(month=2, day=1, year="2026"), row(month=8, day=1, year="2026")])
pump()
short_month = (last_week(), w.calendar_box.get_preferred_height())
w._select(1)
pump()
long_month = (last_week(), w.calendar_box.get_preferred_height())
check("Aug 2026 needs six weeks", long_month[0], 6)
check("Feb 2026 needs fewer", short_month[0] < 6, True)
check("calendar height is the same", short_month[1], long_month[1])

# ...and the same again when each month is the first thing shown.
heights = []
for month in (2, 8, 11):
    fresh_settings, fresh, fresh_window = build([row(month=month, day=1, year="2026")])
    heights.append(fresh_window.get_preferred_height()[1])
    fresh_window.destroy()
yearly_settings, yearly, yearly_window = build([row(month=2, day=1, year="", yearly=True)])
heights.append(yearly_window.get_preferred_height()[1])
yearly_window.destroy()
check("editor height never changes", len(set(heights)), 1)

window.destroy()
print()
print("%d failed" % len(failures) if failures else "all passed")
sys.exit(1 if failures else 0)
