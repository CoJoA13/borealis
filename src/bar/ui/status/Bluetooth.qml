/*
    Bluetooth, from BlueZ through KDE's bluez-qt, and (while a page shows
    them) the devices it knows, connected the way Plasma's own applet does.
    SPDX-License-Identifier: GPL-3.0-or-later
*/
import QtQuick
import org.kde.bluezqt as BluezQt
import org.kde.plasma.private.bluetooth as PlasmaBt

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

    property int watching: 0
    property var deviceList: null
    property Component devicesComponent: Component {
        PlasmaBt.DevicesProxyModel {
            hideBlockedDevices: true
            // shared with Plasma's applet, so a connection under way shows in both
            Component.onCompleted: sourceModel = PlasmaBt.SharedDevicesStateProxyModel
        }
    }
    function watchDevices(watch) {
        watching = Math.max(0, watching + (watch ? 1 : -1));
        if (watching > 0 && !deviceList) {
            deviceList = devicesComponent.createObject(bt);
        } else if (watching === 0 && deviceList) {
            const old = deviceList;
            deviceList = null;
            old.destroy(1000);
        }
    }
    function toggleDevice(device, ubi, connected) {
        if (!device) {
            return;
        }
        if (connected) {
            PlasmaBt.SharedDevicesStateProxyModel.registerDisconnectingCallForDeviceUbi(device.disconnectFromDevice(), ubi);
        } else {
            PlasmaBt.SharedDevicesStateProxyModel.registerConnectingCallForDeviceUbi(device.connectToDevice(), ubi);
        }
    }
    function pairDevice() {
        PlasmaBt.LaunchApp.launchWizard();
    }
}
