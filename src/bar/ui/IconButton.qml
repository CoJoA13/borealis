/*
    A round icon button for the bar's panels.
    SPDX-License-Identifier: GPL-3.0-or-later
*/
import QtQuick
import org.kde.kirigami as Kirigami

Rectangle {
    id: button

    property string iconName
    property string tip
    property int size: 30
    property bool checked: false
    signal clicked()

    readonly property color fg: Kirigami.Theme.textColor
    width: size
    height: size
    radius: size / 2
    color: checked ? Kirigami.Theme.highlightColor
         : hover.hovered ? Qt.rgba(fg.r, fg.g, fg.b, 0.14) : Qt.rgba(fg.r, fg.g, fg.b, 0.06)
    Accessible.name: tip

    Kirigami.Icon {
        anchors.centerIn: parent
        width: Math.round(button.size * 0.55)
        height: width
        source: button.iconName
        color: button.checked ? Kirigami.Theme.highlightedTextColor : Kirigami.Theme.textColor
    }
    HoverHandler {
        id: hover
        cursorShape: Qt.PointingHandCursor
    }
    TapHandler {
        onTapped: button.clicked()
    }
}
