/*
    One level of a bar menu: rows with marks, icons, shortcuts and submenu
    arrows, drawn like the dock's menus.
    SPDX-License-Identifier: GPL-3.0-or-later
*/
import QtQuick
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

Card {
    id: menu

    property var entries: []
    property int currentIndex: -1
    signal activated(var entry, real rowY)
    signal hovered(var entry, real rowY)

    readonly property bool hasChecks: entries.some(e => e.check !== undefined)
    readonly property bool hasIcons: entries.some(e => !!(e.icon || e.iconData))

    width: Math.min(440, Math.max(200, column.implicitWidth + 12))
    height: Math.max(40, column.implicitHeight + 12)
    radius: 10

    function selectable(i) {
        const e = entries[i];
        return !!e && e.type !== "separator" && e.enabled !== false;
    }
    function rowY(i) {
        const row = rows.itemAt(i);
        return row ? row.y + column.y : 0;
    }
    function step(direction) {
        let i = currentIndex;
        for (let n = 0; n < entries.length; n++) {
            i = (i + direction + entries.length) % entries.length;
            if (selectable(i)) {
                currentIndex = i;
                return;
            }
        }
    }
    function activateCurrent() {
        if (selectable(currentIndex)) {
            activated(entries[currentIndex], rowY(currentIndex));
        }
    }

    Text {
        visible: menu.entries.length === 0
        anchors.centerIn: parent
        text: "…"
        color: Kirigami.Theme.disabledTextColor
    }

    ColumnLayout {
        id: column
        x: 6
        y: 6
        width: menu.width - 12
        spacing: 0

        Repeater {
            id: rows
            model: menu.entries
            delegate: Item {
                id: row
                required property var modelData
                required property int index
                readonly property bool separator: modelData.type === "separator"
                readonly property bool usable: modelData.enabled !== false
                readonly property bool highlighted: menu.currentIndex === index && menu.selectable(index)
                readonly property color ink: highlighted ? Kirigami.Theme.highlightedTextColor
                    : usable ? Kirigami.Theme.textColor : Kirigami.Theme.disabledTextColor

                Layout.fillWidth: true
                implicitHeight: separator ? 9 : 28
                implicitWidth: separator ? 0 : line.implicitWidth + 20

                Rectangle {
                    visible: row.separator
                    anchors.centerIn: parent
                    width: parent.width - 16
                    height: 1
                    color: Qt.rgba(menu.fg.r, menu.fg.g, menu.fg.b, 0.12)
                }
                Rectangle {
                    anchors.fill: parent
                    radius: 6
                    visible: row.highlighted
                    color: Kirigami.Theme.highlightColor
                }
                RowLayout {
                    id: line
                    visible: !row.separator
                    anchors.fill: parent
                    anchors.leftMargin: 10
                    anchors.rightMargin: 10
                    spacing: 8
                    Text {
                        visible: menu.hasChecks
                        Layout.preferredWidth: 14
                        horizontalAlignment: Text.AlignHCenter
                        text: row.modelData.check === true ? (row.modelData.radio ? "●" : "✓") : ""
                        color: row.ink
                        font.pointSize: Kirigami.Theme.defaultFont.pointSize
                    }
                    Item {
                        visible: menu.hasIcons
                        Layout.preferredWidth: 16
                        Layout.preferredHeight: 16
                        Kirigami.Icon {
                            anchors.fill: parent
                            visible: !row.modelData.iconData
                            source: row.modelData.icon || ""
                            opacity: row.usable ? 1 : 0.4
                        }
                        Image {
                            anchors.fill: parent
                            visible: !!row.modelData.iconData
                            source: row.modelData.iconData || ""
                            sourceSize: Qt.size(32, 32)
                            opacity: row.usable ? 1 : 0.4
                        }
                    }
                    Text {
                        Layout.fillWidth: true
                        text: row.modelData.text || ""
                        textFormat: Text.PlainText
                        elide: Text.ElideRight
                        color: row.ink
                        font.pointSize: Kirigami.Theme.defaultFont.pointSize
                    }
                    Text {
                        visible: !!row.modelData.shortcut
                        text: row.modelData.shortcut || ""
                        color: row.highlighted ? Kirigami.Theme.highlightedTextColor : Kirigami.Theme.disabledTextColor
                        font.pointSize: Kirigami.Theme.smallFont.pointSize
                    }
                    Text {
                        visible: row.modelData.type === "submenu"
                        text: "›"
                        color: row.ink
                        font.pointSize: Kirigami.Theme.defaultFont.pointSize * 1.2
                    }
                }
                MouseArea {
                    anchors.fill: parent
                    hoverEnabled: true
                    enabled: menu.selectable(row.index)
                    onEntered: {
                        menu.currentIndex = row.index;
                        menu.hovered(row.modelData, row.y + column.y);
                    }
                    onClicked: menu.activated(row.modelData, row.y + column.y)
                }
            }
        }
    }
}
