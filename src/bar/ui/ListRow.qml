/*
    A row on a Control Center page: an icon, a name and a line under it, a
    check mark or a spinner at the end, and room for a switch or buttons.
    SPDX-License-Identifier: GPL-3.0-or-later
*/
import QtQuick
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

Rectangle {
    id: row

    property string iconName
    property string title
    property string subtitle
    property bool checked: false
    property bool busy: false
    property bool interactive: true
    property bool highlighted: false
    default property alias trailing: trailingRow.data
    signal clicked()

    readonly property color fg: Kirigami.Theme.textColor
    implicitHeight: Math.max(44, body.implicitHeight + 12)
    implicitWidth: body.implicitWidth + 20
    radius: 10
    color: highlighted ? Qt.rgba(fg.r, fg.g, fg.b, 0.1)
         : hover.hovered && interactive ? Qt.rgba(fg.r, fg.g, fg.b, 0.08) : "transparent"
    Accessible.name: title
    Accessible.description: subtitle
    Accessible.role: Accessible.ListItem

    RowLayout {
        id: body
        anchors.fill: parent
        anchors.leftMargin: 10
        anchors.rightMargin: 10
        spacing: 10

        Kirigami.Icon {
            visible: row.iconName !== ""
            source: row.iconName
            Layout.preferredWidth: 22
            Layout.preferredHeight: 22
        }
        ColumnLayout {
            Layout.fillWidth: true
            spacing: 0
            Text {
                Layout.fillWidth: true
                text: row.title
                textFormat: Text.PlainText
                elide: Text.ElideRight
                font.pointSize: Kirigami.Theme.defaultFont.pointSize
                font.weight: row.checked ? Font.DemiBold : Font.Normal
                color: Kirigami.Theme.textColor
            }
            Text {
                Layout.fillWidth: true
                visible: text.length > 0
                text: row.subtitle
                textFormat: Text.PlainText
                elide: Text.ElideRight
                font.pointSize: Kirigami.Theme.smallFont.pointSize
                color: Kirigami.Theme.disabledTextColor
            }
        }
        RowLayout {
            id: trailingRow
            spacing: 6
        }
        Kirigami.Icon {
            visible: row.busy
            source: "view-refresh"
            Layout.preferredWidth: 16
            Layout.preferredHeight: 16
            RotationAnimator on rotation {
                running: row.busy && row.visible
                from: 0
                to: 360
                duration: 1000
                loops: Animation.Infinite
            }
        }
        Kirigami.Icon {
            visible: row.checked && !row.busy
            source: "checkmark"
            color: Kirigami.Theme.highlightColor
            Layout.preferredWidth: 16
            Layout.preferredHeight: 16
        }
    }
    HoverHandler {
        id: hover
        enabled: row.interactive
        cursorShape: Qt.PointingHandCursor
    }
    TapHandler {
        enabled: row.interactive
        onTapped: row.clicked()
    }
}
