/*
    The Control Center's page behind its power button: sleep, restart, shut
    down or log out, each confirmed on Plasma's own screen once the Control
    Center is out of the way.
    SPDX-License-Identifier: GPL-3.0-or-later
*/
import QtQuick
import QtQuick.Layouts
import ".."

ColumnLayout {
    id: page

    required property var center
    readonly property var can: bar.sessionCapabilities || ({})
    readonly property var choices: [
        {key: "sleep", text: qsTr("Sleep"), icon: "system-suspend", can: "suspend"},
        {key: "restart", text: qsTr("Restart…"), icon: "system-reboot", can: "reboot"},
        {key: "shutdown", text: qsTr("Shut Down…"), icon: "system-shutdown", can: "shutdown"},
        {key: "logout", text: qsTr("Log Out…"), icon: "system-log-out", can: "logout"}
    ]

    spacing: 4

    PageHeader {
        Layout.fillWidth: true
        title: qsTr("Sleep, Restart or Shut Down")
        onBack: page.center.back()
    }

    Repeater {
        model: page.choices
        delegate: ListRow {
            required property var modelData
            objectName: "session-" + modelData.key
            Layout.fillWidth: true
            // what this computer (or its policy) doesn't allow stays out of sight
            visible: page.can[modelData.can] !== false
            iconName: modelData.icon
            title: modelData.text
            onClicked: {
                page.center.dismissed();
                bar.sessionRequested(modelData.key);
            }
        }
    }
}
