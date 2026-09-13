/*
    A Control Center toggle: a rounded pill with an icon, a name and what it's
    set to, lit up while on. Toggles with more to them have an arrow at the end
    that opens their page; in edit mode the end removes the toggle instead.
    SPDX-License-Identifier: GPL-3.0-or-later
*/
import QtQuick
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

Rectangle {
    id: pill

    property string label
    property string sub
    property string iconName
    property bool on: false
    property bool hasDetails: false
    property bool editing: false
    property bool dimmed: false          // not on this computer (shown while editing)
    property bool lifted: false          // being dragged
    signal toggled()
    signal detailsRequested()
    signal removeRequested()

    readonly property color fg: Kirigami.Theme.textColor
    readonly property bool lit: on && !editing
    readonly property color ink: lit ? Kirigami.Theme.highlightedTextColor : Kirigami.Theme.textColor

    implicitHeight: 52
    implicitWidth: 160
    radius: height / 2
    scale: lifted ? 1.04 : 1
    color: lit ? Kirigami.Theme.highlightColor
         : mainHover.hovered && !editing ? Qt.rgba(fg.r, fg.g, fg.b, 0.14) : Qt.rgba(fg.r, fg.g, fg.b, lifted ? 0.16 : 0.07)
    border.width: editing ? 1 : 0
    border.color: Qt.rgba(fg.r, fg.g, fg.b, 0.22)
    Accessible.name: label
    Accessible.description: sub
    Accessible.role: Accessible.Button
    Accessible.checkable: true
    Accessible.checked: on
    Behavior on color {
        ColorAnimation {
            duration: 120
        }
    }
    Behavior on scale {
        NumberAnimation {
            duration: 100
        }
    }

    Item {
        id: main
        anchors.left: parent.left
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        anchors.right: end.left
        opacity: pill.dimmed ? 0.5 : 1

        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: 14
            anchors.rightMargin: end.visible ? 4 : 12
            spacing: 8
            Kirigami.Icon {
                source: pill.iconName
                color: pill.ink
                Layout.preferredWidth: 20
                Layout.preferredHeight: 20
            }
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 0
                Text {
                    Layout.fillWidth: true
                    text: pill.label
                    textFormat: Text.PlainText
                    elide: Text.ElideRight
                    font.weight: Font.DemiBold
                    font.pointSize: Kirigami.Theme.defaultFont.pointSize
                    color: pill.ink
                }
                Text {
                    Layout.fillWidth: true
                    visible: text.length > 0
                    text: pill.sub
                    textFormat: Text.PlainText
                    elide: Text.ElideRight
                    font.pointSize: Kirigami.Theme.smallFont.pointSize
                    color: pill.ink
                    opacity: 0.8
                }
            }
        }
        HoverHandler {
            id: mainHover
            cursorShape: pill.editing ? Qt.OpenHandCursor : Qt.PointingHandCursor
        }
        TapHandler {
            enabled: !pill.editing
            onTapped: pill.toggled()
        }
    }

    Item {
        id: end
        objectName: "pill-end"
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        width: pill.editing || pill.hasDetails ? 38 : 0
        visible: width > 0

        Rectangle {
            visible: pill.hasDetails && !pill.editing
            anchors.left: parent.left
            anchors.verticalCenter: parent.verticalCenter
            width: 1
            height: parent.height - 24
            color: pill.ink
            opacity: 0.25
        }
        Rectangle {
            anchors.centerIn: parent
            width: 30
            height: 30
            radius: 15
            color: pill.editing ? Qt.rgba(pill.fg.r, pill.fg.g, pill.fg.b, endHover.hovered ? 0.22 : 0.12)
                 : endHover.hovered ? Qt.rgba(pill.ink.r, pill.ink.g, pill.ink.b, 0.16) : "transparent"
            Kirigami.Icon {
                anchors.centerIn: parent
                width: 16
                height: 16
                source: pill.editing ? "list-remove" : "go-next"
                color: pill.ink
            }
        }
        HoverHandler {
            id: endHover
            cursorShape: Qt.PointingHandCursor
        }
        TapHandler {
            gesturePolicy: TapHandler.ReleaseWithinBounds
            onTapped: pill.editing ? pill.removeRequested() : pill.detailsRequested()
        }
    }
}
