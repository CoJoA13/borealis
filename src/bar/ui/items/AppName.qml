/*
    The name of the app in front, in bold; clicking it opens its first menu.
    SPDX-License-Identifier: GPL-3.0-or-later
*/
import QtQuick
import org.kde.kirigami as Kirigami
import ".."

BarButton {
    id: button

    property var window
    readonly property string appName: bar.windows.active.name || ""

    readonly property bool wanted: appName.length > 0

    name: "app"
    visible: wanted
    implicitWidth: label.implicitWidth + 16

    Text {
        id: label
        anchors.centerIn: parent
        text: button.appName
        textFormat: Text.PlainText
        font.bold: true
        font.pointSize: Kirigami.Theme.defaultFont.pointSize
        color: Kirigami.Theme.textColor
    }

    onClicked: {
        const titles = bar.appmenu.titles;
        if (titles.length > 0) {
            const r = button.windowRect();
            bar.openAppMenu(titles[0].key, button.window.targetScreen, r.x, r.y, r.width, r.height);
        }
    }
}
