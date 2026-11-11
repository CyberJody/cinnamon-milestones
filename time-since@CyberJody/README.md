# Time Since

A desklet that shows how long it has been since a date and time — or how long until one — in days, hours and minutes (seconds optional). One desklet can hold several trackers, stacked top to bottom.

It sets no colors of its own, so it picks up your Cinnamon theme's text and desklet background and changes when you switch themes.

## Usage

1. Right-click the desktop → **Add Desklets**, add **Time Since**.
2. Right-click the desklet → **Configure…**
3. Under **Trackers**, click **+**, then fill in the tracker below the table.

Past dates count up ("Since …"); future dates count down ("Until …") and switch to counting up once they pass.

## Editing a tracker

Select a tracker in the table and change it with the controls underneath. Changes are saved as you make them, so the desklet updates while you edit.

- **Title** – shown above the counter (optional)
- **Date** – pick the month, type the year, and click the day in the calendar. The calendar always matches the month: February offers 28 or 29 days, and with a year it lines the days up under their weekdays.
- **Time** – type the hour and minutes and choose **AM**, **PM** or **24H**. Hours are 1–12 with AM/PM and 0–23 with 24H; a blank hour means midnight.
- **Monthly** – repeats on the chosen day every month. The calendar becomes a plain 1–31 picker; shorter months use their last day (31st → Nov 30).
- **Yearly** – birthdays, anniversaries; repeats on the chosen month and day every year. Feb 29 falls on Feb 28 in non-leap years.

Repeating trackers have no year, so the Year box is hidden for them. They count down to the next occurrence and start over once it arrives.

The line under the form spells out what the tracker counts to ("Tuesday, November 10, 2026 at 9:30 PM.") or says what is still missing ("Enter a year, or tick Monthly or Yearly.").

In the table, **Show** hides a tracker without deleting it, and the arrow buttons change the order trackers appear in on the desklet.

## Backup

**Back up to a file…** and **Restore from a file…** save and load all trackers and display options. They use the same file format as the settings window's own Export / Import menu items. Restoring replaces the current list.

## Display options

- **Show seconds** – tick every second instead of every minute
- **Show the "Since / Until" line** – the target date under each title
- **Size** – scale the whole desklet
