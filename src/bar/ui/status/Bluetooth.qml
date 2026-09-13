/*
    Bluetooth, from BlueZ through KDE's bluez-qt.
    SPDX-License-Identifier: GPL-3.0-or-later
*/
import QtQuick
import org.kde.bluezqt as BluezQt

QtObject {
    id: bt

    readonly property var manager: BluezQt.Manager
    readonly property bool available: manager.operational && manager.adapters.length > 0
    readonly property var adapter: manager.usableAdapter
    readonly property bool on: available && !manager.bluetoothBlocked && !!adapter && adapter.powered
    readonly property var connectedDevices: manager.connectedDevices || []
    readonly property string label: !on ? qsTr("Off")
        : connectedDevices.length === 1 ? connectedDevices[0].name
        : connectedDevices.length > 1 ? qsTr("%1 devices").arg(connectedDevices.length) : qsTr("On")

    function toggle() {
        const turnOn = !bt.on;
        manager.bluetoothBlocked = !turnOn;
        for (let i = 0; i < manager.adapters.length; i++) {
            manager.adapters[i].powered = turnOn;
        }
    }
}
