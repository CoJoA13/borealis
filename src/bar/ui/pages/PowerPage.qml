/*
    The Control Center's Power page: the battery, the power mode, and Stay
    Awake.
    SPDX-License-Identifier: GPL-3.0-or-later
*/
import QtQuick
import QtQuick.Layouts
import org.kde.kirigami as Kirigami
import ".."

ColumnLayout {
    id: page

    required property var center
    readonly property var power: center.status ? center.status.power : null

    // power-profiles-daemon's reasons, in words
    function reason(blocked, code) {
        if (blocked) {
            return code === "lap-detected" ? qsTr("Off while the computer may be on your lap")
                : code === "high-operating-temperature" ? qsTr("Off while the computer is too hot")
                : qsTr("Not available right now");
        }
        return code === "lap-detected" ? qsTr("Slower while the computer may be on your lap")
            : code === "high-operating-temperature" ? qsTr("Slower while the computer is too hot")
            : qsTr("May run slower right now");
    }
    function heldBy(profile) {
        const holds = page.power ? page.power.holds.filter(hold => hold.Profile === profile) : [];
        return holds.length > 0 ? qsTr("Asked for by %1").arg(holds.map(hold => hold.Name).join(", ")) : "";
    }

    spacing: 4

    PageHeader {
        Layout.fillWidth: true
        title: qsTr("Power")
        onBack: page.center.back()
    }

    RowLayout {
        visible: bar.battery.present
        Layout.fillWidth: true
        Layout.leftMargin: 10
        Layout.topMargin: 4
        Layout.bottomMargin: 4
        spacing: 12
        Kirigami.Icon {
            source: page.center.batteryIcon(bar.battery.percent, bar.battery.charging)
            Layout.preferredWidth: 32
            Layout.preferredHeight: 32
        }
        ColumnLayout {
            spacing: 0
            Text {
                text: bar.battery.percent + "%"
                font.pointSize: Kirigami.Theme.defaultFont.pointSize * 1.4
                font.weight: Font.DemiBold
                font.features: { "tnum": 1 }
                color: Kirigami.Theme.textColor
            }
            Text {
                text: bar.battery.status
                font.pointSize: Kirigami.Theme.smallFont.pointSize
                color: Kirigami.Theme.disabledTextColor
            }
        }
    }

    SectionLabel {
        visible: page.center.profiles.length > 0
        text: qsTr("Power Mode")
    }
    Repeater {
        model: page.center.profiles
        delegate: ListRow {
            required property string modelData
            readonly property bool blocked: modelData === "performance" && !!page.power && page.power.performanceBlocked !== ""
            readonly property bool degraded: modelData === "performance" && !!page.power && page.power.performanceDegraded !== ""
            objectName: "profile-" + modelData
            Layout.fillWidth: true
            iconName: page.center.profileIcon(modelData)
            title: page.center.profileNames[modelData] || modelData
            subtitle: blocked ? page.reason(true, page.power.performanceBlocked)
                : degraded ? page.reason(false, page.power.performanceDegraded)
                : page.heldBy(modelData)
            checked: modelData === page.center.profile
            interactive: !blocked
            opacity: blocked ? 0.55 : 1
            onClicked: page.center.setProfile(modelData)
        }
    }

    ListRow {
        objectName: "awake"
        visible: !!page.power
        Layout.fillWidth: true
        Layout.topMargin: 4
        iconName: page.power && page.power.awake ? "system-suspend-inhibited" : "system-suspend-uninhibited"
        title: qsTr("Stay Awake")
        subtitle: qsTr("No sleeping or locking by itself")
        onClicked: page.power.setAwake(!page.power.awake)
        ToggleSwitch {
            checked: !!page.power && page.power.awake
            tip: qsTr("Stay Awake")
            onToggled: on => page.power.setAwake(on)
        }
    }

    RowLayout {
        Layout.fillWidth: true
        Layout.topMargin: 4
        Item {
            Layout.fillWidth: true
        }
        TextButton {
            text: qsTr("Power Settings…")
            onClicked: {
                page.center.dismissed();
                bar.openKcm("kcm_powerdevilprofilesconfig");
            }
        }
    }
}
