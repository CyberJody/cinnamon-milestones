# Time Since

A desklet that shows how long it has been since a date and time — or how long until one — in days, hours and minutes (seconds optional). One desklet can hold several trackers, stacked top to bottom.

It sets no colors of its own, so it picks up your Cinnamon theme's text and desklet background and changes when you switch themes.

## Usage

1. Right-click the desktop → **Add Desklets**, add **Time Since**.
2. Right-click the desklet → **Configure…**
3. Under **Trackers**, click **+** and enter a title, date and time.

Past dates count up ("Since …"); future dates count down ("Until …") and switch to counting up once they pass.

## Tracker fields

Every field except the title is a picker, so there is nothing to format.

- **Show** – untick to hide a tracker without deleting it
- **Title** – shown above the counter (optional)
- **Month / Day** – the date
- **Year** – typed, 4 digits. Leave blank for Monthly and Yearly trackers.
- **Hr / AM/PM / Min** – the time. Hour is 1–12 with AM or PM, or 0–23 with 24H.
- **Monthly** – repeats on the chosen day every month; month and year are ignored. Days past the end of a month fall on its last day (31st → Nov 30).
- **Yearly** – birthdays, anniversaries; repeats on the chosen month and day every year; year is ignored. Feb 29 falls on Feb 28 in non-leap years.

A repeating tracker counts down to its next occurrence and starts over once it arrives. A one-off tracker counts down to a future date or up from a past one.

Use the arrow buttons to reorder. An impossible date (e.g. February 31) shows an error on the desklet instead of a counter.

## Backup

**Back up to a file…** and **Restore from a file…** save and load all trackers and display options. They use the same file format as the settings window's own Export / Import menu items. Restoring replaces the current list.

## Display options

- **Show seconds** – tick every second instead of every minute
- **Show the "Since / Until" line** – the target date under each title
- **Size** – scale the whole desklet
