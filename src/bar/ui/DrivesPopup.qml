/*
    The removable drives: open one, or unmount and power it off so it can be
    pulled out.
    SPDX-License-Identifier: GPL-3.0-or-later
*/
import QtQuick
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

Card {
    id: popup

    signal dismissed()

    function size(bytes) {
        const units = ["B", "KB", "MB", "GB", "TB"];
        let value = bytes;
        let unit = 0;
        while (value >= 1000 && unit < units.length - 1) {
            value /= 1000;
            unit++;
        }
        return (value >= 10 || unit === 0 ? Math.round(value) : value.toFixed(1)) + " " + units[unit];
    }

    width: 340
    height: column.implicitHeight + 28
    focus: true
    Keys.onEscapePressed: dismissed()

    ColumnLayout {
        id: column
        x: 14
        y: 14
        width: popup.width - 28
        spacing: 8

        Text {
            text: qsTr("Drives")
            font.bold: true
            font.pointSize: Kirigami.Theme.defaultFont.pointSize * 1.05
            color: Kirigami.Theme.textColor
        }
        Text {
            visible: bar.drives.drives.length === 0
            text: qsTr("No removable drives")
            color: Kirigami.Theme.disabledTextColor
            font.pointSize: Kirigami.Theme.defaultFont.pointSize
        }
        Repeater {
            model: bar.drives.drives
            delegate: RowLayout {
                id: row
                required property var modelData
                Layout.fillWidth: true
                spacing: 10
                Kirigami.Icon {
                    source: "drive-removable-media"
                    Layout.preferredWidth: 26
                    Layout.preferredHeight: 26
                }
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 0
                    Text {
                        Layout.fillWidth: true
                        text: row.modelData.label
                        textFormat: Text.PlainText
                        elide: Text.ElideRight
                        color: Kirigami.Theme.textColor
                        font.pointSize: Kirigami.Theme.defaultFont.pointSize
                    }
                    Text {
                        Layout.fillWidth: true
                        text: popup.size(row.modelData.size) + (row.modelData.mounted ? qsTr(" · in use") : "")
                        color: Kirigami.Theme.disabledTextColor
                        font.pointSize: Kirigami.Theme.smallFont.pointSize
                    }
                }
                IconButton {
                    iconName: "document-open-folder"
                    tip: qsTr("Open")
                    onClicked: {
                        bar.drives.open(row.modelData.path);
                        popup.dismissed();
                    }
                }
                IconButton {
                    iconName: "media-eject"
                    tip: qsTr("Safely remove")
                    onClicked: bar.drives.remove(row.modelData.path)
                }
            }
        }
    }
}
