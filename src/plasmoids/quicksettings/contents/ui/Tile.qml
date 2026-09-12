/*
    One quick-settings tile: icon, label, on/off. Hidden when its backend
    isn't there, so a missing service can't leave a dead button behind.
    SPDX-License-Identifier: GPL-3.0-or-later
*/

import QtQuick
import QtQuick.Layouts
import org.kde.kirigami as Kirigami
import org.kde.plasma.components as PlasmaComponents3

Item {
    id: tile

    property string label
    property string sub
    property string iconName
    property bool active: false
    property bool available: true
    property bool busy: false
    signal toggled()

    visible: available
    implicitWidth: Kirigami.Units.gridUnit * 9
    implicitHeight: Kirigami.Units.gridUnit * 3.4
    Layout.fillWidth: true

    Rectangle {
        anchors.fill: parent
        radius: Kirigami.Units.cornerRadius > 0 ? Kirigami.Units.cornerRadius : 8
        color: tile.active ? Kirigami.Theme.highlightColor
             : mouse.containsMouse ? Qt.rgba(Kirigami.Theme.textColor.r, Kirigami.Theme.textColor.g,
                                             Kirigami.Theme.textColor.b, 0.12)
             : Qt.rgba(Kirigami.Theme.textColor.r, Kirigami.Theme.textColor.g,
                       Kirigami.Theme.textColor.b, 0.06)
        Behavior on color { ColorAnimation { duration: Kirigami.Units.shortDuration } }

        RowLayout {
            anchors.fill: parent
            anchors.margins: Kirigami.Units.smallSpacing * 1.5
            spacing: Kirigami.Units.smallSpacing

            Kirigami.Icon {
                source: tile.iconName
                Layout.preferredWidth: Kirigami.Units.iconSizes.smallMedium
                Layout.preferredHeight: Kirigami.Units.iconSizes.smallMedium
                color: tile.active ? Kirigami.Theme.highlightedTextColor : Kirigami.Theme.textColor
                isMask: true
                opacity: tile.busy ? 0.4 : 1
            }

            ColumnLayout {
                spacing: 0
                Layout.fillWidth: true
                PlasmaComponents3.Label {
                    text: tile.label
                    elide: Text.ElideRight
                    Layout.fillWidth: true
                    color: tile.active ? Kirigami.Theme.highlightedTextColor : Kirigami.Theme.textColor
                }
                PlasmaComponents3.Label {
                    text: tile.sub
                    visible: text.length > 0
                    elide: Text.ElideRight
                    Layout.fillWidth: true
                    opacity: 0.7
                    font: Kirigami.Theme.smallFont
                    color: tile.active ? Kirigami.Theme.highlightedTextColor : Kirigami.Theme.textColor
                }
            }
        }

        MouseArea {
            id: mouse
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: tile.toggled()
        }
    }
}
