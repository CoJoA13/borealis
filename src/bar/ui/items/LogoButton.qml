/*
    The Borealis menu's button, at the start of the bar.
    SPDX-License-Identifier: GPL-3.0-or-later
*/
import QtQuick
import org.kde.kirigami as Kirigami
import ".."

BarButton {
    id: button

    property var window

    name: "system"
    active: bar.popup === "system"
    implicitWidth: height + 6

    Kirigami.Icon {
        anchors.centerIn: parent
        width: 18
        height: 18
        source: bar.logo
        fallback: "start-here-kde-symbolic"
    }

    onClicked: {
        const r = button.windowRect();
        bar.openSystemMenu(button.window.targetScreen, r.x, r.y, r.width, r.height);
    }
}
