/*
    The dock's menu, drawn to match the dock: frosted, rounded, compact, and
    usable from the keyboard.
    SPDX-License-Identifier: GPL-3.0-or-later
*/
import QtQuick
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

Rectangle {
    id: menu

    property var entries: []
    property int currentIndex: -1
    signal triggered(string key)
    signal dismissed()

    Kirigami.Theme.colorSet: Kirigami.Theme.Window
    Kirigami.Theme.inherit: false
    readonly property color fg: Kirigami.Theme.textColor

    width: Math.min(460, Math.max(220, column.implicitWidth + 12))
    height: column.implicitHeight + 12
    radius: 12
    color: Qt.rgba(Kirigami.Theme.backgroundColor.r, Kirigami.Theme.backgroundColor.g,
                   Kirigami.Theme.backgroundColor.b, 0.86)
    border.width: 1
    border.color: Qt.rgba(fg.r, fg.g, fg.b, 0.14)
    focus: true

    function selectable(i) {
        const e = entries[i];
        return !!e && (e.type === "command" || e.type === "window") && e.enabled !== false;
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
    function activate(i) {
        if (selectable(i)) {
            triggered(entries[i].key);
        }
    }

    Keys.onUpPressed: step(-1)
    Keys.onDownPressed: step(1)
    Keys.onReturnPressed: activate(currentIndex)
    Keys.onEnterPressed: activate(currentIndex)
    Keys.onEscapePressed: dismissed()

    // clicks inside the menu never reach the overlay behind it
    MouseArea {
        anchors.fill: parent
        acceptedButtons: Qt.AllButtons
    }

    ColumnLayout {
        id: column
        x: 6
        y: 6
        width: menu.width - 12
        spacing: 0

        Repeater {
            model: menu.entries
            delegate: Item {
                id: row
                required property var modelData
                required property int index
                readonly property bool separator: modelData.type === "separator"
                readonly property bool header: modelData.type === "header"
                readonly property bool usable: modelData.enabled !== false
                readonly property bool highlighted: menu.currentIndex === index && menu.selectable(index)

                Layout.fillWidth: true
                implicitHeight: separator ? 9 : header ? 28 : 30
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
                    radius: 7
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
                        visible: row.modelData.check !== undefined
                        text: row.modelData.check === true ? "✓" : ""
                        Layout.preferredWidth: 14
                        color: row.highlighted ? Kirigami.Theme.highlightedTextColor : Kirigami.Theme.textColor
                        font.pointSize: Kirigami.Theme.defaultFont.pointSize
                    }
                    Kirigami.Icon {
                        visible: !!row.modelData.icon
                        source: row.modelData.icon || ""
                        Layout.preferredWidth: 16
                        Layout.preferredHeight: 16
                        opacity: row.usable ? 1 : 0.4
                    }
                    Text {
                        Layout.fillWidth: true
                        text: row.modelData.text || ""
                        textFormat: Text.PlainText          // window titles and song names are not markup
                        elide: Text.ElideRight
                        font.bold: row.modelData.type === "window" && row.modelData.check === true
                        font.pointSize: Kirigami.Theme.defaultFont.pointSize
                        color: row.highlighted ? Kirigami.Theme.highlightedTextColor
                            : (!row.usable || row.header || row.modelData.dim === true)
                                ? Kirigami.Theme.disabledTextColor : Kirigami.Theme.textColor
                    }
                }
                MouseArea {
                    anchors.fill: parent
                    hoverEnabled: true
                    enabled: menu.selectable(row.index)
                    onEntered: menu.currentIndex = row.index
                    onClicked: menu.activate(row.index)
                }
            }
        }
    }
}
