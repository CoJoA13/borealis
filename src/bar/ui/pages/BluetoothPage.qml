/*
    The Control Center's Bluetooth page: the switch and the devices Bluetooth
    knows, each connected or disconnected with a click.
    SPDX-License-Identifier: GPL-3.0-or-later
*/
import QtQuick
import QtQuick.Layouts
import org.kde.kirigami as Kirigami
import ".."

ColumnLayout {
    id: page

    required property var center
    readonly property var bt: center.status ? center.status.bt : null
    readonly property bool usable: !!bt && bt.on

    spacing: 8

    Component.onCompleted: if (bt) {
        bt.watchDevices(true);
    }
    Component.onDestruction: if (bt) {
        bt.watchDevices(false);
    }

    PageHeader {
        Layout.fillWidth: true
        title: qsTr("Bluetooth")
        switchVisible: !!page.bt && page.bt.available
        checked: page.usable
        onBack: page.center.back()
        onToggled: on => {
            if (on !== page.bt.on) {
                page.bt.toggle();
            }
        }
    }

    Text {
        Layout.fillWidth: true
        Layout.margins: 10
        visible: text.length > 0
        text: !page.bt || !page.bt.available ? qsTr("There's no Bluetooth adapter.")
            : !page.bt.on ? qsTr("Bluetooth is off.")
            : list.count === 0 ? qsTr("No devices yet. Pair one to see it here.") : ""
        wrapMode: Text.WordWrap
        horizontalAlignment: Text.AlignHCenter
        font.pointSize: Kirigami.Theme.defaultFont.pointSize
        color: Kirigami.Theme.disabledTextColor
    }

    ListView {
        id: list
        objectName: "devices"
        Layout.fillWidth: true
        Layout.preferredHeight: Math.min(contentHeight, Math.max(140, page.center.maxHeight - 170))
        visible: page.usable && count > 0
        clip: true
        spacing: 2
        boundsBehavior: Flickable.StopAtBounds
        model: page.usable && page.bt.deviceList ? page.bt.deviceList : null

        delegate: ListRow {
            required property var model
            required property int index
            readonly property bool moving: model.Connecting === true || model.Disconnecting === true
            objectName: "device-" + index
            width: ListView.view.width
            iconName: model.Icon || "preferences-system-bluetooth"
            title: model.DeviceFullName || model.Name || ""
            subtitle: model.Connecting ? qsTr("Connecting…")
                : model.Disconnecting ? qsTr("Disconnecting…")
                : model.ConnectionFailed ? qsTr("Couldn't connect")
                : model.Connected ? (model.Battery ? qsTr("Connected · battery %1%").arg(model.Battery.percentage)
                                                   : qsTr("Connected"))
                : model.Paired ? qsTr("Paired") : ""
            checked: model.Connected === true
            busy: moving
            onClicked: if (!moving) {
                page.bt.toggleDevice(model.Device, model.Ubi, model.Connected === true);
            }
        }
    }

    RowLayout {
        Layout.fillWidth: true
        spacing: 6
        TextButton {
            visible: page.usable
            text: qsTr("Pair a Device…")
            onClicked: {
                page.center.dismissed();
                page.bt.pairDevice();
            }
        }
        Item {
            Layout.fillWidth: true
        }
        TextButton {
            text: qsTr("Bluetooth Settings…")
            onClicked: {
                page.center.dismissed();
                bar.openKcm("kcm_bluetooth");
            }
        }
    }
}
