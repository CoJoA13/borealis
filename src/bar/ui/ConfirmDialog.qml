/*
    A question before something that can't be undone (Force Quit).
    SPDX-License-Identifier: GPL-3.0-or-later
*/
import QtQuick
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

Card {
    id: dialog

    property string title
    property string text
    property string label
    signal accepted()
    signal dismissed()

    width: 380
    height: column.implicitHeight + 36
    focus: true
    Keys.onEscapePressed: dismissed()
    Keys.onReturnPressed: accepted()

    ColumnLayout {
        id: column
        x: 18
        y: 18
        width: dialog.width - 36
        spacing: 10
        Text {
            Layout.fillWidth: true
            text: dialog.title
            textFormat: Text.PlainText
            wrapMode: Text.Wrap
            font.bold: true
            font.pointSize: Kirigami.Theme.defaultFont.pointSize * 1.1
            color: Kirigami.Theme.textColor
        }
        Text {
            Layout.fillWidth: true
            text: dialog.text
            textFormat: Text.PlainText
            wrapMode: Text.Wrap
            color: Kirigami.Theme.textColor
            opacity: 0.8
            font.pointSize: Kirigami.Theme.defaultFont.pointSize
        }
        RowLayout {
            Layout.fillWidth: true
            Layout.topMargin: 6
            Item {
                Layout.fillWidth: true
            }
            TextButton {
                text: qsTr("Cancel")
                onClicked: dialog.dismissed()
            }
            TextButton {
                text: dialog.label
                destructive: true
                onClicked: dialog.accepted()
            }
        }
    }
}
