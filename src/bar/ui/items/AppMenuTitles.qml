/*
    The menus of the app in front (File, Edit, View…). Titles that don't fit
    before the middle of the bar fade out rather than run into the clock.
    SPDX-License-Identifier: GPL-3.0-or-later
*/
import QtQuick
import org.kde.kirigami as Kirigami
import ".."

Row {
    id: titles

    property var window
    property real limit: 1e9

    readonly property bool wanted: bar.appmenu.titles.length > 0

    height: parent ? parent.height : 24
    visible: wanted

    Repeater {
        model: bar.appmenu.titles
        delegate: BarButton {
            id: title
            required property var modelData
            readonly property bool fits: title.x + title.width <= titles.limit

            name: "app:" + modelData.key
            height: titles.height
            width: label.implicitWidth + 16
            active: bar.popup === name
            opacity: fits ? 1 : 0
            enabled: fits && modelData.enabled

            Text {
                id: label
                anchors.centerIn: parent
                text: title.modelData.text
                textFormat: Text.PlainText
                font.pointSize: Kirigami.Theme.defaultFont.pointSize
                color: Kirigami.Theme.textColor
            }

            onClicked: {
                const r = title.windowRect();
                bar.openAppMenu(title.modelData.key, titles.window.targetScreen, r.x, r.y, r.width, r.height);
            }
        }
    }
}
