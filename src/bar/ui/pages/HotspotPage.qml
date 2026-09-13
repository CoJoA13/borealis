/*
    The Control Center's Hotspot page: share this computer's connection over
    Wi-Fi, under a name and password of your choosing.
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
    readonly property bool active: !!net && net.hotspotActive
    readonly property bool canStart: !!net && net.on && !net.airplane && net.hotspotSupported
    readonly property bool ready: canStart && name.text.length > 0 && password.acceptable

    function start() {
        if (page.ready) {
            page.net.startHotspot(name.text, password.text);
        }
    }

    spacing: 6

    Component.onCompleted: if (net) {
        net.readHotspot();
    }

    PageHeader {
        Layout.fillWidth: true
        title: qsTr("Hotspot")
        switchVisible: !!page.net
        switchEnabled: page.active || page.ready
        checked: page.active
        onBack: page.center.back()
        onToggled: on => {
            if (on) {
                page.start();
            } else {
                page.net.stopHotspot();
            }
        }
    }

    Text {
        Layout.fillWidth: true
        Layout.leftMargin: 10
        Layout.rightMargin: 10
        Layout.bottomMargin: 4
        wrapMode: Text.WordWrap
        font.pointSize: Kirigami.Theme.defaultFont.pointSize
        color: Kirigami.Theme.disabledTextColor
        text: !page.net ? qsTr("Network management isn't available.")
            : page.active ? qsTr("Your other devices can join this network with the password below.")
            : page.net.airplane ? qsTr("Airplane mode is on.")
            : !page.net.on ? qsTr("Turn Wi-Fi on to share this computer's connection.")
            : !page.net.hotspotSupported ? qsTr("Your Wi-Fi is busy with a network. Disconnect from it first, or plug in a second Wi-Fi adapter.")
            : qsTr("Share this computer's connection with your other devices over Wi-Fi.")
    }

    SectionLabel {
        text: qsTr("Network name")
    }
    Field {
        id: name
        objectName: "hotspot-name"
        Layout.fillWidth: true
        Layout.leftMargin: 4
        Layout.rightMargin: 4
        enabled: !page.active
        text: page.net ? page.net.hotspotName : ""
        placeholder: qsTr("Name")
    }
    SectionLabel {
        text: qsTr("Password")
    }
    Field {
        id: password
        objectName: "hotspot-password"
        Layout.fillWidth: true
        Layout.leftMargin: 4
        Layout.rightMargin: 4
        enabled: !page.active
        password: true
        minimumLength: 8
        text: page.net ? page.net.hotspotPassword : ""
        placeholder: qsTr("At least 8 characters")
        onAccepted: page.start()
    }

    RowLayout {
        Layout.fillWidth: true
        Layout.topMargin: 6
        spacing: 6
        TextButton {
            text: qsTr("Network Settings…")
            onClicked: {
                page.center.dismissed();
                bar.openKcm("kcm_networkmanagement");
            }
        }
        Item {
            Layout.fillWidth: true
        }
        TextButton {
            objectName: "hotspot-start"
            primary: true
            text: page.active ? qsTr("Stop") : qsTr("Start")
            enabled: page.active || page.ready
            onClicked: {
                if (page.active) {
                    page.net.stopHotspot();
                } else {
                    page.start();
                }
            }
        }
    }
}
