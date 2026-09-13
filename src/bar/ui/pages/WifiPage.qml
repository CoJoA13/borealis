/*
    The Control Center's Wi-Fi page: the switch, the networks in reach, and
    joining one (with its password typed right here when it needs one).
    SPDX-License-Identifier: GPL-3.0-or-later
*/
import QtQuick
import QtQuick.Layouts
import org.kde.kirigami as Kirigami
import ".."

ColumnLayout {
    id: page

    required property var center
    readonly property var net: center.status ? center.status.net : null
    readonly property bool usable: !!net && net.on && !net.airplane
    // the network showing its buttons or password field, by name
    property string openKey: ""

    spacing: 8

    Component.onCompleted: if (net) {
        net.watchNetworks(true);
        net.scan();
    }
    Component.onDestruction: if (net) {
        net.watchNetworks(false);
    }

    // Plasma's applet looks again every ten seconds while it's open
    Timer {
        interval: 10200
        repeat: true
        running: page.usable && page.visible
        onTriggered: page.net.scan()
    }

    PageHeader {
        Layout.fillWidth: true
        title: qsTr("Wi-Fi")
        switchVisible: !!page.net && page.net.wifiAvailable
        checked: page.usable
        busy: page.usable && page.net.scanning
        onBack: page.center.back()
        onToggled: on => {
            if (page.net.airplane) {
                page.net.setAirplane(false);
            } else if (on !== page.net.on) {
                page.net.toggle();
            }
        }
    }

    Text {
        Layout.fillWidth: true
        Layout.margins: 10
        visible: text.length > 0
        text: !page.net ? qsTr("Network management isn't available.")
            : page.net.airplane ? qsTr("Airplane mode is on.")
            : !page.net.on ? qsTr("Wi-Fi is off.")
            : list.count === 0 ? qsTr("Looking for networks…") : ""
        wrapMode: Text.WordWrap
        horizontalAlignment: Text.AlignHCenter
        font.pointSize: Kirigami.Theme.defaultFont.pointSize
        color: Kirigami.Theme.disabledTextColor
    }
    TextButton {
        Layout.alignment: Qt.AlignHCenter
        visible: !!page.net && page.net.airplane
        text: qsTr("Turn Off Airplane Mode")
        onClicked: page.net.setAirplane(false)
    }

    ListView {
        id: list
        objectName: "networks"
        Layout.fillWidth: true
        Layout.preferredHeight: Math.min(contentHeight, Math.max(140, page.center.maxHeight - 170))
        visible: page.usable && count > 0
        clip: true
        spacing: 2
        boundsBehavior: Flickable.StopAtBounds
        model: page.usable && page.net.networks ? page.net.networks : null

        delegate: ColumnLayout {
            id: network

            required property var model
            required property int index
            readonly property int connectionState: model.ConnectionState
            readonly property bool connected: connectionState === page.net.activated
            readonly property bool busy: connectionState === page.net.activating
                || connectionState === page.net.deactivating
            readonly property bool open: page.openKey !== "" && page.openKey === model.ItemUniqueName
            readonly property bool asksPassword: page.net.asksForPassword(model.SecurityType, model.Uuid)
            readonly property var row: ({uuid: model.Uuid, connectionPath: model.ConnectionPath,
                                         devicePath: model.DevicePath, specificPath: model.SpecificPath})

            function join() {
                if (password.acceptable) {
                    page.net.connectTo(network.row, password.text);
                    page.openKey = "";
                    page.center.forceActiveFocus();
                }
            }

            width: ListView.view.width
            spacing: 4
            onOpenChanged: {
                if (page.net) {
                    page.net.holdRow(index, open && asksPassword);
                }
                if (open && asksPassword) {
                    password.focusInput();
                }
            }

            ListRow {
                objectName: "network-" + network.index
                Layout.fillWidth: true
                iconName: network.model.ConnectionIcon || "network-wireless"
                title: network.model.ItemUniqueName || ""
                subtitle: network.connectionState === page.net.activating ? qsTr("Connecting…")
                    : network.connectionState === page.net.deactivating ? qsTr("Disconnecting…")
                    : network.connected ? qsTr("Connected") : network.model.Uuid ? qsTr("Saved") : ""
                checked: network.connected
                busy: network.busy
                highlighted: network.open
                onClicked: {
                    if (network.connected || network.busy || network.asksPassword) {
                        page.openKey = network.open ? "" : network.model.ItemUniqueName;
                    } else {
                        page.net.connectTo(network.row, "");
                    }
                }
            }
            RowLayout {
                visible: network.open && (network.connected || network.busy)
                Layout.fillWidth: true
                Layout.leftMargin: 42
                Layout.bottomMargin: 4
                spacing: 6
                TextButton {
                    objectName: "disconnect"
                    text: qsTr("Disconnect")
                    onClicked: {
                        page.net.disconnectFrom(network.row);
                        page.openKey = "";
                    }
                }
                TextButton {
                    text: qsTr("Settings…")
                    onClicked: {
                        page.center.dismissed();
                        bar.openKcm("kcm_networkmanagement");
                    }
                }
            }
            RowLayout {
                visible: network.open && network.asksPassword && !network.connected && !network.busy
                Layout.fillWidth: true
                Layout.leftMargin: 42
                Layout.bottomMargin: 4
                spacing: 6
                Field {
                    id: password
                    objectName: "password"
                    Layout.fillWidth: true
                    password: true
                    placeholder: qsTr("Password")
                    minimumLength: page.net.shortestPassword(network.model.SecurityType)
                    catchesEscape: true
                    onAccepted: network.join()
                    onCancelled: {
                        page.openKey = "";
                        page.center.forceActiveFocus();
                    }
                }
                TextButton {
                    objectName: "join"
                    text: qsTr("Join")
                    primary: true
                    enabled: password.acceptable
                    onClicked: network.join()
                }
            }
        }
    }

    RowLayout {
        Layout.fillWidth: true
        Item {
            Layout.fillWidth: true
        }
        TextButton {
            text: qsTr("Network Settings…")
            onClicked: {
                page.center.dismissed();
                bar.openKcm("kcm_networkmanagement");
            }
        }
    }
}
