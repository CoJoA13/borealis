/*
    A Control Center toggle: a rounded pill with an icon, a name and what it's
    set to, lit up while on.
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
    signal toggled()

    readonly property color fg: Kirigami.Theme.textColor
    readonly property color ink: on ? Kirigami.Theme.highlightedTextColor : Kirigami.Theme.textColor

    implicitHeight: 52
    implicitWidth: 160
    radius: height / 2
    color: on ? Kirigami.Theme.highlightColor
         : hover.hovered ? Qt.rgba(fg.r, fg.g, fg.b, 0.14) : Qt.rgba(fg.r, fg.g, fg.b, 0.07)
    Behavior on color {
        ColorAnimation {
            duration: 120
        }
    }

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: 16
        anchors.rightMargin: 12
        spacing: 10
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
        id: hover
        cursorShape: Qt.PointingHandCursor
    }
    TapHandler {
        onTapped: pill.toggled()
    }
}
