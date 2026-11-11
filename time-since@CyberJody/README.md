# Time Since

A desklet that shows how long it has been since a date and time — or how long until one — in days, hours and minutes (seconds optional). One desklet can hold several trackers, stacked top to bottom.

It sets no colors of its own, so it picks up your Cinnamon theme's text and desklet background and changes when you switch themes.

## Usage

1. Right-click the desktop → **Add Desklets**, add **Time Since**.
2. Right-click the desklet → **Configure…**
3. Under **Trackers**, click **+** and enter a title, date and time.

Past dates count up ("Since …"); future dates count down ("Until …") and switch to counting up once they pass.

## Tracker fields

Every field is a picker, so there is nothing to type except the title.

- **Show** – untick to hide a tracker without deleting it
- **Title** – shown above the counter (optional)
- **Repeat**
  - **Never** – counts to or from one exact date and time
  - **Yearly** – birthdays, anniversaries; counts down to the next one and starts over. The year is ignored. Feb 29 falls on Feb 28 in non-leap years.
  - **Every Monday … Every Sunday** – weekly; counts down to the next one at the chosen time. The date is ignored.
- **Month / Day / Year** – the date
- **Hour / Min** – the time

Use the arrow buttons to reorder. An impossible date (e.g. February 31) shows an error on the desklet instead of a counter.

## Backup

**Back up to a file…** and **Restore from a file…** save and load all trackers and display options. They use the same file format as the settings window's own Export / Import menu items. Restoring replaces the current list.

## Display options

- **Show seconds** – tick every second instead of every minute
- **Show the "Since / Until" line** – the target date under each title
- **Size** – scale the whole desklet
