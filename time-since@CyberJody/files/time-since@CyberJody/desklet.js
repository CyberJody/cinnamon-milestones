const Desklet = imports.ui.desklet;
const Settings = imports.ui.settings;
const St = imports.gi.St;
const Clutter = imports.gi.Clutter;
const Pango = imports.gi.Pango;
const GLib = imports.gi.GLib;
const Gettext = imports.gettext;

const UUID = "time-since@CyberJody";
Gettext.bindtextdomain(UUID, GLib.get_home_dir() + "/.local/share/locale");

function _(str) {
    return Gettext.dgettext(UUID, str);
}

const MINUTE = 60;
const HOUR = 60 * MINUTE;
const DAY = 24 * HOUR;

const MONTHS = ["jan", "feb", "mar", "apr", "may", "jun",
                "jul", "aug", "sep", "oct", "nov", "dec"];

// Accepts 2026-11-10, 2026/11/10, 11/10/2026, 11-10-2026, "Nov 10 2026",
// "10 Nov 2026", "November 10, 2026". Returns {y, m, d} or null.
function parseDate(text) {
    let s = (text || "").trim().toLowerCase().replace(/,/g, " ").replace(/\s+/g, " ");
    if (!s) return null;
    let m;
    if ((m = s.match(/^(\d{4})[-\/.](\d{1,2})[-\/.](\d{1,2})$/)))
        return { y: +m[1], m: +m[2], d: +m[3] };
    if ((m = s.match(/^(\d{1,2})[-\/.](\d{1,2})[-\/.](\d{4})$/)))
        return { y: +m[3], m: +m[1], d: +m[2] };            // US order: M/D/Y
    if ((m = s.match(/^([a-z]+)\.? (\d{1,2})(?:st|nd|rd|th)? (\d{4})$/))) {
        let mi = MONTHS.indexOf(m[1].slice(0, 3));
        if (mi >= 0) return { y: +m[3], m: mi + 1, d: +m[2] };
    }
    if ((m = s.match(/^(\d{1,2})(?:st|nd|rd|th)? ([a-z]+)\.? (\d{4})$/))) {
        let mi = MONTHS.indexOf(m[2].slice(0, 3));
        if (mi >= 0) return { y: +m[3], m: mi + 1, d: +m[1] };
    }
    return null;
}

// Accepts 21:30, 21:30:15, 9:30 PM, 9:30pm, 9pm, 9 am, noon, midnight,
// or empty (midnight). Returns {h, m, s} or null.
function parseTime(text) {
    let s = (text || "").trim().toLowerCase().replace(/\./g, "");
    if (!s || s === "midnight") return { h: 0, m: 0, s: 0 };
    if (s === "noon") return { h: 12, m: 0, s: 0 };
    let m = s.match(/^(\d{1,2})(?::(\d{2}))?(?::(\d{2}))?\s*(am|pm|a|p)?$/);
    if (!m) return null;
    let h = +m[1], min = +(m[2] || 0), sec = +(m[3] || 0);
    let ap = m[4];
    if (ap) {
        if (h < 1 || h > 12) return null;
        if (ap[0] === "p" && h !== 12) h += 12;
        if (ap[0] === "a" && h === 12) h = 0;
    }
    if (h > 23 || min > 59 || sec > 59) return null;
    return { h, m: min, s: sec };
}

function toDateTime(date, time) {
    try {
        return GLib.DateTime.new_local(date.y, date.m, date.d, time.h, time.m, time.s);
    } catch (e) {
        return null;    // e.g. Feb 30
    }
}

class TimeSinceDesklet extends Desklet.Desklet {
    constructor(metadata, deskletId) {
        super(metadata, deskletId);
        this._timeoutId = 0;

        // Read v1.0's single-tracker values before DeskletSettings loads:
        // its schema upgrade drops keys that no longer exist.
        let legacy = this._readLegacyTracker(deskletId);

        this.settings = new Settings.DeskletSettings(this, UUID, deskletId);
        this.settings.bind("trackers", "trackers", this._rebuild);
        this.settings.bind("show-seconds", "showSeconds", this._rebuild);
        this.settings.bind("show-since-line", "showSinceLine", this._rebuild);
        this.settings.bind("scale", "scale", this._rebuild);

        if (legacy && (this.trackers || []).length === 0)
            this.trackers = [legacy];

        // No hardcoded colors anywhere: text, borders and background all
        // come from the active Cinnamon theme, so the desklet follows theme
        // changes automatically.
        this._box = new St.BoxLayout({ vertical: true, style_class: "time-since-box" });
        this.setContent(this._box);
        this.setHeader(_("Time Since"));
    }

    // Version 1.0 stored one tracker in title/target-date/target-time.
    // Returns that tracker as a list row, or null if there isn't one.
    _readLegacyTracker(deskletId) {
        try {
            let path = GLib.build_filenamev([GLib.get_user_config_dir(),
                "cinnamon", "spices", UUID, `${deskletId}.json`]);
            let [ok, bytes] = GLib.file_get_contents(path);
            if (!ok) return null;
            let data = JSON.parse(new TextDecoder().decode(bytes));
            if (data["trackers"] || !data["target-date"] || !data["target-date"].value)
                return null;
            let d = data["target-date"].value;
            let t = (data["target-time"] && data["target-time"].value) || { h: 0, m: 0 };
            let pad = n => String(n).padStart(2, "0");
            return {
                enabled: true,
                title: (data["title"] && data["title"].value) || "",
                date: `${d.y}-${pad(d.m)}-${pad(d.d)}`,
                time: `${pad(t.h)}:${pad(t.m)}`
            };
        } catch (e) {
            return null;
        }
    }

    _label(text, styleClass, fontEm) {
        let l = new St.Label({
            text: text,
            style_class: styleClass,
            x_align: Clutter.ActorAlign.CENTER,
            x_expand: true
        });
        l.clutter_text.ellipsize = Pango.EllipsizeMode.NONE;
        l.set_style(`font-size: ${fontEm * this.scale}em;`);
        return l;
    }

    _makeUnit(value, label) {
        let unit = new St.BoxLayout({ vertical: true, style_class: "time-since-unit" });
        let num = new St.Label({
            text: String(value),
            style_class: "time-since-number",
            x_align: Clutter.ActorAlign.CENTER
        });
        let lbl = new St.Label({
            text: label,
            style_class: "time-since-label",
            x_align: Clutter.ActorAlign.CENTER
        });
        num.set_style(`font-size: ${2.4 * this.scale}em;`);
        lbl.set_style(`font-size: ${0.8 * this.scale}em;`);
        unit.add_actor(num);
        unit.add_actor(lbl);
        return unit;
    }

    _makeTracker(tracker, now) {
        let box = new St.BoxLayout({
            vertical: true,
            style_class: "time-since-tracker",
            x_align: Clutter.ActorAlign.CENTER,
            x_expand: true
        });

        if (tracker.title)
            box.add_actor(this._label(tracker.title, "time-since-title", 1.1));

        let date = parseDate(tracker.date);
        let time = parseTime(tracker.time);
        let target = date && time ? toDateTime(date, time) : null;

        if (!target) {
            let bad = !date ? _("Can't read date") + `: "${tracker.date || ""}"`
                            : !time ? _("Can't read time") + `: "${tracker.time || ""}"`
                                    : _("No such date") + `: "${tracker.date}"`;
            box.add_actor(this._label(bad, "time-since-sub", 0.85));
            return box;
        }

        let diffSec = Math.floor(now.difference(target) / 1000000); // µs → s
        let future = diffSec < 0;
        let s = Math.abs(diffSec);

        let days = Math.floor(s / DAY);
        let hours = Math.floor((s % DAY) / HOUR);
        let minutes = Math.floor((s % HOUR) / MINUTE);
        let seconds = s % MINUTE;

        if (this.showSinceLine) {
            let when = target.format("%b %-d, %Y %-l:%M %p");
            box.add_actor(this._label((future ? _("Until") : _("Since")) + " " + when,
                                      "time-since-sub", 0.85));
        }

        let units = new St.BoxLayout({
            style_class: "time-since-units",
            x_align: Clutter.ActorAlign.CENTER,
            x_expand: true
        });
        units.add_actor(this._makeUnit(days, days === 1 ? _("day") : _("days")));
        units.add_actor(this._makeUnit(hours, hours === 1 ? _("hour") : _("hours")));
        units.add_actor(this._makeUnit(minutes, minutes === 1 ? _("min") : _("mins")));
        if (this.showSeconds)
            units.add_actor(this._makeUnit(seconds, seconds === 1 ? _("sec") : _("secs")));
        box.add_actor(units);

        return box;
    }

    _update() {
        this._box.destroy_all_children();
        let now = GLib.DateTime.new_now_local();
        let active = (this.trackers || []).filter(t => t.enabled !== false);

        if (active.length === 0) {
            this._box.add_actor(this._label(_("Time Since"), "time-since-title", 1.1));
            this._box.add_actor(this._label(_("Right-click → Configure to add a tracker"),
                                            "time-since-sub", 0.85));
        } else {
            active.forEach((t, i) => {
                if (i > 0)
                    this._box.add_actor(new St.Widget({
                        style_class: "time-since-separator",
                        x_expand: true
                    }));
                this._box.add_actor(this._makeTracker(t, now));
            });
        }
        this._fitWidth();
    }

    _fitWidth() {
        // The desklet frame caches its first measured width and won't grow
        // when a wider line appears, which clips the text. Pin the box to
        // its natural width so the frame always fits the widest line.
        this._box.set_width(-1);
        let [, natural] = this._box.get_preferred_width(-1);
        this._box.set_width(natural);
    }

    _schedule() {
        this._stopTimer();
        // Fire on the next second/minute boundary so the display ticks in
        // step with the system clock, then reschedule.
        let now = GLib.DateTime.new_now_local();
        let ms = Math.floor(now.get_microsecond() / 1000);
        let delayMs = this.showSeconds ? 1000 - ms
                                       : (60 - now.get_second()) * 1000 - ms;
        this._timeoutId = GLib.timeout_add(GLib.PRIORITY_DEFAULT, Math.max(delayMs, 50), () => {
            this._timeoutId = 0;
            this._update();
            this._schedule();
            return GLib.SOURCE_REMOVE;
        });
    }

    _stopTimer() {
        if (this._timeoutId) {
            GLib.source_remove(this._timeoutId);
            this._timeoutId = 0;
        }
    }

    _rebuild() {
        this._update();
        this._schedule();
    }

    on_desklet_added_to_desktop() {
        this._rebuild();
    }

    on_desklet_removed() {
        this._stopTimer();
        if (this.settings) {
            // Cinnamon calls this after a fade-out, so on reload the new
            // instance may already have registered under the same id.
            // Only finalize if the registry still points at us; otherwise
            // finalize() would unregister the new instance and the settings
            // window could no longer push live changes to it.
            const Main = imports.ui.main;
            let reg = Main.settingsManager.uuids[UUID];
            let id = this.settings.instanceId;
            if (reg && reg[id] && reg[id] !== this.settings) {
                for (let key in this.settings.bindings)
                    this.settings.unbindAll(key);
                this.settings.disconnectAll();
            } else {
                this.settings.finalize();
            }
            this.settings = null;
        }
    }
}

function main(metadata, deskletId) {
    return new TimeSinceDesklet(metadata, deskletId);
}
