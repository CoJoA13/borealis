/*
    Real aurora activity from NOAA's planetary K-index.

    Opt-in (Settings › "Follow real aurora activity"): this is the only part of
    Borealis that talks to the network. It asks services.swpc.noaa.gov for the
    current Kp every 20 minutes, sends nothing but the request itself, and keeps
    the last value if the fetch fails.
    SPDX-License-Identifier: GPL-3.0-or-later
*/

import QtQuick
import org.kde.notification as KNotification

Item {
    id: sky

    // NOAA's estimated Kp, 0 (quiet) to 9 (severe storm); -1 = not known yet
    property real kp: -1
    property bool alerts: false
    property real alertAt: 5
    readonly property bool storm: kp >= alertAt
    // quiet nights stay subtle, a real storm blazes
    readonly property real factor: kp < 0 ? 1.0 : 0.55 + 0.11 * Math.min(9, kp)

    readonly property string liveUrl: "https://services.swpc.noaa.gov/json/planetary_k_index_1m.json"
    readonly property string dailyUrl: "https://services.swpc.noaa.gov/products/noaa-planetary-k-index.json"
    property real lastAlerted: -1

    function fetch(url, onValue, onFail) {
        const req = new XMLHttpRequest();
        req.timeout = 20000;
        req.onreadystatechange = function () {
            if (req.readyState !== XMLHttpRequest.DONE) {
                return;
            }
            if (req.status !== 200) {
                onFail();
                return;
            }
            try {
                onValue(JSON.parse(req.responseText));
            } catch (e) {
                onFail();
            }
        };
        req.ontimeout = onFail;
        req.onerror = onFail;
        req.open("GET", url);
        req.send();
    }

    function latest(rows, keys) {
        for (let i = rows.length - 1; i >= 0; --i) {
            for (const k of keys) {
                const v = Number(rows[i][k]);
                if (rows[i][k] !== undefined && !isNaN(v)) {
                    return v;
                }
            }
        }
        return NaN;
    }

    function apply(value) {
        if (isNaN(value)) {
            return;
        }
        sky.kp = Math.max(0, Math.min(9, value));
        if (sky.alerts && sky.kp >= sky.alertAt && sky.lastAlerted !== Math.floor(sky.kp)) {
            sky.lastAlerted = Math.floor(sky.kp);
            alert.text = i18nd("plasma_wallpaper_org.borealis.aurora",
                               "Planetary K-index %1 — the aurora may be visible tonight.",
                               sky.kp.toFixed(1));
            alert.sendEvent();
        } else if (sky.kp < sky.alertAt) {
            sky.lastAlerted = -1;
        }
    }

    function refresh() {
        fetch(liveUrl,
              rows => apply(latest(rows, ["estimated_kp", "kp_index"])),
              () => fetch(dailyUrl, rows => {
                  // the daily product is [[headers], [row], ...] or objects
                  const row = rows[rows.length - 1];
                  apply(Array.isArray(row) ? Number(row[1]) : Number(row.Kp));
              }, () => {}));
    }

    KNotification.Notification {
        id: alert
        componentName: "plasma_workspace"
        eventId: "notification"
        title: i18nd("plasma_wallpaper_org.borealis.aurora", "Aurora watch")
        iconName: "weather-clear-night"
        urgency: KNotification.Notification.NormalUrgency
    }

    Timer {
        interval: 20 * 60 * 1000
        running: true
        repeat: true
        triggeredOnStart: true
        onTriggered: sky.refresh()
    }
}
