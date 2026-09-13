/*
    The icons apps keep in the tray. A click does what the app asks for (often
    showing its window); a right click opens its menu; a middle click is the
    app's second action; the wheel scrolls it.
    SPDX-License-Identifier: GPL-3.0-or-later
*/
import QtQuick
import org.kde.kirigami as Kirigami
import ".."

Row {
    id: tray

    property var window

    readonly property bool wanted: repeater.count > 0

    height: parent ? parent.height : 24
    visible: wanted

    Repeater {
        id: repeater
        model: bar.tray.items.filter(i => (bar.settings.values.trayHidden || []).indexOf(i.id) < 0)
        delegate: BarButton {
            id: icon
            required property var modelData

            name: "tray:" + modelData.key
            width: tray.height
            height: tray.height
            active: bar.popup === name

            Kirigami.Icon {
                anchors.centerIn: parent
                width: 16
                height: 16
                source: icon.modelData.iconUrl || icon.modelData.iconName || "application-x-executable"
            }

            onClicked: mouseButton => {
                const r = icon.windowRect();
                const screen = tray.window.targetScreen;
                const gx = Math.round(screen.geometry.x + r.x + r.width / 2);
                const gy = Math.round(screen.geometry.y + r.y + r.height);
                if (mouseButton === Qt.RightButton || (icon.modelData.itemIsMenu && icon.modelData.menu)) {
                    bar.openTrayMenu(icon.modelData.key, screen, r.x, r.y, r.width, r.height);
                } else if (mouseButton === Qt.MiddleButton) {
                    bar.tray.secondaryActivate(icon.modelData.key, gx, gy);
                } else {
                    bar.tray.activate(icon.modelData.key, gx, gy);
                }
            }
            onScrolled: (delta, horizontal) => bar.tray.scroll(icon.modelData.key, delta, horizontal ? "horizontal" : "vertical")
        }
    }
}
