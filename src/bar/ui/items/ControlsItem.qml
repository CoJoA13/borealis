/*
    The Control Center's button: network, Bluetooth, sound and battery at a
    glance.
    SPDX-License-Identifier: GPL-3.0-or-later
*/
import QtQuick
import org.kde.kirigami as Kirigami
import ".."

BarButton {
    id: controls

    property var window
    readonly property var status: window ? window.status : null
    readonly property bool showNet: !!status && !!status.net && status.net.available
    readonly property bool showBt: !!status && !!status.bt && status.bt.on
    readonly property bool showSound: !!status && !!status.sound && status.sound.available

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
            visible: bar.battery.present
            spacing: 3
            Kirigami.Icon {
                anchors.verticalCenter: parent.verticalCenter
                source: controls.batteryIcon(bar.battery.percent, bar.battery.charging)
                width: 16
                height: 16
            }
            Text {
                anchors.verticalCenter: parent.verticalCenter
                text: bar.battery.percent + "%"
                font.pointSize: Kirigami.Theme.smallFont.pointSize
                font.features: { "tnum": 1 }
                color: Kirigami.Theme.textColor
            }
        }
        Kirigami.Icon {
            anchors.verticalCenter: parent.verticalCenter
            visible: !controls.showNet && !controls.showBt && !controls.showSound && !bar.battery.present
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
