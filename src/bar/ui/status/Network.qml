/*
    The network, from Plasma's network management module.
    SPDX-License-Identifier: GPL-3.0-or-later
*/
import QtQuick
import org.kde.plasma.networkmanagement as PlasmaNM

QtObject {
    id: net

    property var enabledConnections: PlasmaNM.EnabledConnections {}
    property var devices: PlasmaNM.AvailableDevices {}
    property var wireless: PlasmaNM.WirelessStatus {}
    property var handler: PlasmaNM.Handler {}
    property var connectionIcon: PlasmaNM.ConnectionIcon {}

    readonly property bool wifiAvailable: !!devices.wirelessDeviceAvailable
    readonly property bool available: wifiAvailable || !!devices.wiredDeviceAvailable
    readonly property bool on: !!enabledConnections.wirelessEnabled
    readonly property string ssid: wireless.wifiSSID || ""
    readonly property string label: !on ? qsTr("Off") : ssid.length ? ssid : qsTr("Not connected")
    readonly property string iconName: connectionIcon.connectionIcon || "network-wireless"

    function toggle() {
        handler.enableWireless(!enabledConnections.wirelessEnabled);
    }
}
