/*
    The network, from Plasma's network management module: Wi-Fi, airplane
    mode, the hotspot, and (while a page shows them) the networks in reach.
    Joining a network the way Plasma's own applet does, so passwords for
    enterprise networks and the like still go through Plasma's dialog.
    SPDX-License-Identifier: GPL-3.0-or-later
*/
import QtQuick
import org.kde.kitemmodels as KItemModels
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
    readonly property string label: airplane ? qsTr("Airplane Mode") : !on ? qsTr("Off")
        : ssid.length ? ssid : qsTr("Not connected")
    readonly property string iconName: connectionIcon.connectionIcon || "network-wireless"
    readonly property bool scanning: !!handler.scanning

    // airplane mode: Wi-Fi, mobile data and Bluetooth off together
    readonly property bool airplaneAvailable: wifiAvailable || !!devices.modemDeviceAvailable
    readonly property bool airplane: !!PlasmaNM.Configuration.airplaneModeEnabled

    // sharing this computer's connection over Wi-Fi. Plasma's settings don't
    // announce changes to the hotspot's name and password, so they're read
    // when wanted (the Hotspot page asks as it opens) rather than bound
    readonly property bool hotspotSupported: !!handler.hotspotSupported
    readonly property bool hotspotActive: !!handler.hotspotActive
    property string hotspotName: ""
    property string hotspotPassword: ""
    function readHotspot() {
        hotspotName = PlasmaNM.Configuration.hotspotName || "";
        hotspotPassword = PlasmaNM.Configuration.hotspotPassword || "";
    }
    Component.onCompleted: readHotspot()

    // connection states, for the pages
    readonly property int activating: PlasmaNM.Enums.Activating
    readonly property int activated: PlasmaNM.Enums.Activated
    readonly property int deactivating: PlasmaNM.Enums.Deactivating

    function toggle() {
        handler.enableWireless(!enabledConnections.wirelessEnabled);
    }
    function setAirplane(enable) {
        handler.enableAirplaneMode(enable);
        PlasmaNM.Configuration.airplaneModeEnabled = enable;
    }
    function scan() {
        if (on && !airplane) {
            handler.requestScan();
        }
    }

    // a network never joined before, with a password typed right here
    function asksForPassword(securityType, uuid) {
        return !uuid && [PlasmaNM.Enums.StaticWep, PlasmaNM.Enums.WpaPsk, PlasmaNM.Enums.Wpa2Psk,
                         PlasmaNM.Enums.SAE].indexOf(securityType) >= 0;
    }
    function shortestPassword(securityType) {
        return securityType === PlasmaNM.Enums.StaticWep ? 5 : 8;
    }
    // row: {uuid, connectionPath, devicePath, specificPath} from the list
    function connectTo(row, password) {
        if (row.uuid) {
            handler.activateConnection(row.connectionPath, row.devicePath, row.specificPath);
        } else if (password) {
            handler.addAndActivateConnection(row.devicePath, row.specificPath, password);
        } else {
            handler.addAndActivateConnection(row.devicePath, row.specificPath);
        }
    }
    function disconnectFrom(row) {
        handler.deactivateConnection(row.connectionPath, row.devicePath);
    }

    function startHotspot(name, password) {
        PlasmaNM.Configuration.hotspotName = name;
        PlasmaNM.Configuration.hotspotPassword = password;
        readHotspot();
        handler.createHotspot();
    }
    function stopHotspot() {
        handler.stopHotspot();
    }

    // the Wi-Fi networks in reach, sorted the way Plasma sorts them, kept
    // only while a page shows them
    property int watching: 0
    property var networks: null
    property Component networksComponent: Component {
        KItemModels.KSortFilterProxyModel {
            id: wifiOnly
            property var everything: PlasmaNM.NetworkModel {}
            property var sorted: PlasmaNM.AppletProxyModel {
                sourceModel: wifiOnly.everything
            }
            sourceModel: sorted
            filterRowCallback: function (row, parent) {
                const index = sourceModel.index(row, 0, parent);
                return sourceModel.data(index, sourceModel.KItemModels.KRoleNames.role("Type"))
                    === PlasmaNM.Enums.Wireless;
            }
        }
    }
    function watchNetworks(watch) {
        watching = Math.max(0, watching + (watch ? 1 : -1));
        if (watching > 0 && !networks) {
            networks = networksComponent.createObject(net);
        } else if (watching === 0 && networks) {
            const old = networks;
            networks = null;
            old.destroy(1000);
        }
    }
    // keeps a row where it is while its password is being typed
    function holdRow(row, hold) {
        if (networks && row >= 0 && row < networks.rowCount()) {
            networks.setData(networks.index(row, 0), hold, PlasmaNM.NetworkModel.DelayModelUpdatesRole);
        }
    }
}
