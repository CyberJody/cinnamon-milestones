const Desklet = imports.ui.desklet;
const Settings = imports.ui.settings;
const St = imports.gi.St;
const Clutter = imports.gi.Clutter;
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

class TimeSinceDesklet extends Desklet.Desklet {
    constructor(metadata, deskletId) {
        super(metadata, deskletId);
        this._timeoutId = 0;

        this.settings = new Settings.DeskletSettings(this, UUID, deskletId);
        this.settings.bind("title", "title", this._rebuild);
        this.settings.bind("target-date", "targetDate", this._rebuild);
        this.settings.bind("target-time", "targetTime", this._rebuild);
        this.settings.bind("show-seconds", "showSeconds", this._rebuild);
        this.settings.bind("show-since-line", "showSinceLine", this._rebuild);
        this.settings.bind("scale", "scale", this._rebuild);

        this._buildUi();
        this.setHeader(_("Time Since"));
    }

    _buildUi() {
        // No hardcoded colors anywhere: text, borders and background all
        // come from the active Cinnamon theme, so the desklet follows theme
        // changes automatically.
        this._box = new St.BoxLayout({ vertical: true, style_class: "time-since-box" });

        this._titleLabel = new St.Label({
            style_class: "time-since-title",
            x_align: Clutter.ActorAlign.CENTER,
            x_expand: true
        });
        this._unitsBox = new St.BoxLayout({ style_class: "time-since-units" });
        this._sinceLabel = new St.Label({
            style_class: "time-since-sub",
            x_align: Clutter.ActorAlign.CENTER,
            x_expand: true
        });

        this._box.add_actor(this._titleLabel);
        this._box.add_actor(this._unitsBox);
        this._box.add_actor(this._sinceLabel);
        this.setContent(this._box);
    }

    _makeUnit(value, label) {
        let unit = new St.BoxLayout({ vertical: true, style_class: "time-since-unit" });
        let num = new St.Label({ text: String(value), style_class: "time-since-number" });
        let lbl = new St.Label({ text: label, style_class: "time-since-label" });
        num.set_style(`font-size: ${2.4 * this.scale}em;`);
        lbl.set_style(`font-size: ${0.8 * this.scale}em;`);
        unit.add_actor(num);
        unit.add_actor(lbl);
        return unit;
    }

    _targetDateTime() {
        let d = this.targetDate || {};
        let t = this.targetTime || {};
        try {
            let dt = GLib.DateTime.new_local(d.y, d.m, d.d, t.h || 0, t.m || 0, t.s || 0);
            return dt;
        } catch (e) {
            return null;
        }
    }

    _update() {
        let target = this._targetDateTime();
        this._unitsBox.destroy_all_children();

        let titleScale = `font-size: ${1.1 * this.scale}em;`;
        let subScale = `font-size: ${0.85 * this.scale}em;`;
        this._titleLabel.set_style(titleScale);
        this._sinceLabel.set_style(subScale);

        if (!target) {
            this._titleLabel.set_text(this.title || _("Time Since"));
            this._sinceLabel.set_text(_("Right-click → Configure to set a date"));
            return;
        }

        let now = GLib.DateTime.new_now_local();
        let diffSec = Math.floor(now.difference(target) / 1000000); // microseconds → seconds
        let future = diffSec < 0;
        let s = Math.abs(diffSec);

        let days = Math.floor(s / DAY);
        let hours = Math.floor((s % DAY) / HOUR);
        let minutes = Math.floor((s % HOUR) / MINUTE);
        let seconds = s % MINUTE;

        this._titleLabel.set_text(this.title || "");
        this._titleLabel.visible = !!this.title;

        this._unitsBox.add_actor(this._makeUnit(days, days === 1 ? _("day") : _("days")));
        this._unitsBox.add_actor(this._makeUnit(hours, hours === 1 ? _("hour") : _("hours")));
        this._unitsBox.add_actor(this._makeUnit(minutes, minutes === 1 ? _("min") : _("mins")));
        if (this.showSeconds)
            this._unitsBox.add_actor(this._makeUnit(seconds, seconds === 1 ? _("sec") : _("secs")));

        let when = target.format("%b %-d, %Y %-l:%M %p");
        this._sinceLabel.set_text((future ? _("until") : _("since")) + " " + when);
        this._sinceLabel.visible = this.showSinceLine;
    }

    _schedule() {
        this._stopTimer();
        // Fire on the next second/minute boundary so the display ticks in
        // step with the system clock, then reschedule.
        let now = GLib.DateTime.new_now_local();
        let delayMs;
        if (this.showSeconds) {
            delayMs = 1000 - Math.floor(now.get_microsecond() / 1000);
        } else {
            delayMs = (60 - now.get_second()) * 1000 - Math.floor(now.get_microsecond() / 1000);
        }
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
