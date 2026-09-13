/*
    The Control Center's button: network, Bluetooth, sound and battery at a
    glance (whichever the settings keep).
    SPDX-License-Identifier: GPL-3.0-or-later
*/
import QtQuick
import org.kde.kirigami as Kirigami
import ".."

BarButton {
    id: controls

    property var window
    readonly property var status: window ? window.status : null
    readonly property var glyphs: bar.settings.values.glyphs || []
    readonly property bool showNet: glyphs.indexOf("network") >= 0 && !!status && !!status.net && status.net.available
    readonly property bool showBt: glyphs.indexOf("bluetooth") >= 0 && !!status && !!status.bt && status.bt.on
    readonly property bool showSound: glyphs.indexOf("sound") >= 0 && !!status && !!status.sound && status.sound.available
    readonly property bool showBattery: glyphs.indexOf("battery") >= 0 && bar.battery.present

    function batteryIcon(percent, charging) {
        const level = Math.max(0, Math.min(100, Math.round(percent / 10) * 10));
        return "battery-" + String(level).padStart(3, "0") + (charging ? "-charging" : "");
    }

    name: "controls"
    active: bar.popup === "controls"
    implicitWidth: row.implicitWidth + 18

    Row {
        id: row
        anchors.centerIn: parent
        spacing: 8
        Kirigami.Icon {
            anchors.verticalCenter: parent.verticalCenter
            visible: controls.showNet
            source: controls.showNet ? controls.status.net.iconName : ""
            width: 16
            height: 16
        }
        Kirigami.Icon {
            anchors.verticalCenter: parent.verticalCenter
            visible: controls.showBt
            source: "network-bluetooth"
            width: 16
            height: 16
        }
        Kirigami.Icon {
            anchors.verticalCenter: parent.verticalCenter
            visible: controls.showSound
            source: controls.showSound ? controls.status.sound.iconName : ""
            width: 16
            height: 16
        }
        Row {
            anchors.verticalCenter: parent.verticalCenter
            visible: controls.showBattery
            spacing: 3
            Kirigami.Icon {
                anchors.verticalCenter: parent.verticalCenter
                source: controls.batteryIcon(bar.battery.percent, bar.battery.charging)
                width: 16
                height: 16
            }
            Text {
                anchors.verticalCenter: parent.verticalCenter
                visible: bar.settings.values.batteryPercent !== false
                text: bar.battery.percent + "%"
                font.pointSize: Kirigami.Theme.smallFont.pointSize
                font.features: { "tnum": 1 }
                color: Kirigami.Theme.textColor
            }
        }
        // with nothing else to show, a plain button still opens the Control Center
        Kirigami.Icon {
            anchors.verticalCenter: parent.verticalCenter
            visible: !controls.showNet && !controls.showBt && !controls.showSound && !controls.showBattery
            source: "configure"
            width: 16
            height: 16
        }
    }

    onClicked: {
        const r = controls.windowRect();
        bar.openPanel("controls", controls.window.targetScreen, r.x, r.y, r.width, r.height);
    }
}
