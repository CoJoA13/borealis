/*
    The Control Center's Screenshot and Screen Recording pages: what to
    capture, handed to Spectacle once the Control Center is out of the way.
    SPDX-License-Identifier: GPL-3.0-or-later
*/
import QtQuick
import QtQuick.Layouts
import ".."

ColumnLayout {
    id: page

    required property var center
    readonly property bool recording: center.shownPage === "record"
    readonly property var choices: recording ? [
        {key: "record-region", text: qsTr("Record a Region"), icon: "select-rectangular"},
        {key: "record-window", text: qsTr("Record a Window"), icon: "window"},
        {key: "record-screen", text: qsTr("Record the Screen"), icon: "video-display"}
    ] : [
        {key: "region", text: qsTr("Capture a Region"), icon: "select-rectangular"},
        {key: "window", text: qsTr("Capture the Active Window"), icon: "window"},
        {key: "screen", text: qsTr("Capture This Screen"), icon: "video-display"},
        {key: "all", text: qsTr("Capture Every Screen"), icon: "view-fullscreen"}
    ]

    spacing: 4

    PageHeader {
        Layout.fillWidth: true
        title: page.recording ? qsTr("Screen Recording") : qsTr("Screenshot")
        onBack: page.center.back()
    }

    Repeater {
        model: page.choices
        delegate: ListRow {
            required property var modelData
            objectName: "capture-" + modelData.key
            Layout.fillWidth: true
            iconName: modelData.icon
            title: modelData.text
            onClicked: bar.capture(modelData.key)
        }
    }

    RowLayout {
        Layout.fillWidth: true
        Layout.topMargin: 4
        Item {
            Layout.fillWidth: true
        }
        TextButton {
            text: qsTr("Open Spectacle")
            onClicked: bar.capture("open")
        }
    }
}
