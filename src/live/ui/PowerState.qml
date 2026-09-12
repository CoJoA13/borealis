/*
    True while a machine with a battery runs on it.
    SPDX-License-Identifier: GPL-3.0-or-later
*/

import QtQuick
import org.kde.plasma.plasma5support as P5Support

Item {
    readonly property bool onBattery: {
        const bat = power.data["Battery"];
        const ac = power.data["AC Adapter"];
        return bat !== undefined && bat["Has Cumulative"] === true
            && ac !== undefined && ac["Plugged in"] === false;
    }

    P5Support.DataSource {
        id: power
        engine: "powermanagement"
        connectedSources: ["AC Adapter", "Battery"]
        // as in Plasma's own Kickoff: without these, `data` can stay empty
        onSourceAdded: source => {
            disconnectSource(source);
            connectSource(source);
        }
        onSourceRemoved: source => disconnectSource(source)
    }
}
