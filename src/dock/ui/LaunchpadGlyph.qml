/*
    The Launchpad icon: a glassy tile in the accent colour with nine dots,
    drawn rather than taken from the icon theme so it matches the dock.
    SPDX-License-Identifier: GPL-3.0-or-later
*/
import QtQuick
import org.kde.kirigami as Kirigami

Item {
    id: glyph
    readonly property color accent: Kirigami.Theme.highlightColor

    Rectangle {
        id: tile
        anchors.fill: parent
        anchors.margins: parent.width * 0.06
        radius: width * 0.26
        gradient: Gradient {
            GradientStop { position: 0.0; color: Qt.lighter(glyph.accent, 1.22) }
            GradientStop { position: 1.0; color: Qt.darker(glyph.accent, 1.5) }
        }
        border.width: Math.max(1, width * 0.02)
        border.color: Qt.rgba(1, 1, 1, 0.24)

        Grid {
            anchors.centerIn: parent
            columns: 3
            spacing: tile.width * 0.09
            Repeater {
                model: 9
                Rectangle {
                    width: tile.width * 0.16
                    height: width
                    radius: width * 0.32
                    color: Qt.rgba(1, 1, 1, 0.94)
                }
            }
        }
    }
}
