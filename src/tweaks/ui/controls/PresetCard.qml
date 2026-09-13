/*
    Something to pick that changes a lot at once: a drawing of the desktop it
    makes, its name, and a line about it.
    SPDX-License-Identifier: GPL-3.0-or-later
*/
import QtQuick
import QtQuick.Controls as QQC2
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

QQC2.AbstractButton {
    id: card

    property var summary: ({})
    property string subtitle: ""
    property bool selected: false
    property bool removable: false

    signal removeRequested()

    implicitWidth: Kirigami.Units.gridUnit * 11
    implicitHeight: implicitContentHeight + topPadding + bottomPadding
    padding: Kirigami.Units.smallSpacing * 1.5
    hoverEnabled: true
    Accessible.description: subtitle

    background: Rectangle {
        radius: Kirigami.Units.cornerRadius * 2
        color: card.hovered || card.visualFocus
            ? Qt.rgba(Kirigami.Theme.highlightColor.r, Kirigami.Theme.highlightColor.g,
                      Kirigami.Theme.highlightColor.b, 0.14)
            : Qt.rgba(Kirigami.Theme.textColor.r, Kirigami.Theme.textColor.g, Kirigami.Theme.textColor.b, 0.04)
        border.width: card.selected ? 2 : 1
        border.color: card.selected
            ? Kirigami.Theme.highlightColor
            : Qt.rgba(Kirigami.Theme.textColor.r, Kirigami.Theme.textColor.g, Kirigami.Theme.textColor.b, 0.2)
    }

    contentItem: ColumnLayout {
        spacing: Kirigami.Units.smallSpacing
        opacity: card.enabled ? 1 : 0.6

        DesktopThumb {
            Layout.fillWidth: true
            Layout.preferredHeight: Math.round(width * 0.625)
            summary: card.summary
        }
        RowLayout {
            Layout.fillWidth: true
            spacing: Kirigami.Units.smallSpacing
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 0
                QQC2.Label {
                    Layout.fillWidth: true
                    text: card.text
                    font.bold: card.selected
                    elide: Text.ElideRight
                }
                QQC2.Label {
                    Layout.fillWidth: true
                    text: card.subtitle
                    opacity: 0.7
                    font: Kirigami.Theme.smallFont
                    wrapMode: Text.WordWrap
                    maximumLineCount: 2
                    elide: Text.ElideRight
                }
            }
            QQC2.ToolButton {
                visible: card.removable
                Layout.alignment: Qt.AlignTop
                icon.name: "edit-delete"
                display: QQC2.AbstractButton.IconOnly
                text: qsTr("Delete this preset")
                QQC2.ToolTip.text: text
                QQC2.ToolTip.visible: hovered
                onClicked: card.removeRequested()
            }
        }
    }
}
