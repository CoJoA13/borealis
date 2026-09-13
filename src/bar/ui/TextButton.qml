/*
    A rounded text button for the bar's panels and dialogs.
    SPDX-License-Identifier: GPL-3.0-or-later
*/
import QtQuick
import org.kde.kirigami as Kirigami

Rectangle {
    id: button

    property string text
    property bool primary: false
    property bool destructive: false
    signal clicked()

    readonly property color fg: Kirigami.Theme.textColor
    readonly property color tint: destructive ? Kirigami.Theme.negativeTextColor : Kirigami.Theme.highlightColor
    implicitWidth: label.implicitWidth + 28
    implicitHeight: 30
    radius: 8
    color: primary || destructive
        ? Qt.rgba(tint.r, tint.g, tint.b, hover.hovered ? 1.0 : 0.85)
        : Qt.rgba(fg.r, fg.g, fg.b, hover.hovered ? 0.16 : 0.08)

    Text {
        id: label
        anchors.centerIn: parent
        text: button.text
        color: button.primary || button.destructive ? Kirigami.Theme.highlightedTextColor : Kirigami.Theme.textColor
        font.pointSize: Kirigami.Theme.defaultFont.pointSize
    }
    HoverHandler {
        id: hover
        cursorShape: Qt.PointingHandCursor
    }
    TapHandler {
        onTapped: button.clicked()
    }
}
