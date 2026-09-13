/*
    The frosted, rounded card every popup of the bar is drawn on. Clicks inside
    never reach the overlay behind, which would close it.
    SPDX-License-Identifier: GPL-3.0-or-later
*/
import QtQuick
import org.kde.kirigami as Kirigami

Rectangle {
    id: card

    property real opacityLevel: 0.88
    readonly property color fg: Kirigami.Theme.textColor

    Kirigami.Theme.colorSet: Kirigami.Theme.Window
    Kirigami.Theme.inherit: false

    radius: 14
    color: Qt.rgba(Kirigami.Theme.backgroundColor.r, Kirigami.Theme.backgroundColor.g,
                   Kirigami.Theme.backgroundColor.b, opacityLevel)
    border.width: 1
    border.color: Qt.rgba(fg.r, fg.g, fg.b, 0.14)

    MouseArea {
        anchors.fill: parent
        acceptedButtons: Qt.AllButtons
    }
}
