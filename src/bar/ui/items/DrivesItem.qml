/*
    Shown while a removable drive is plugged in.
    SPDX-License-Identifier: GPL-3.0-or-later
*/
import QtQuick
import org.kde.kirigami as Kirigami
import ".."

BarButton {
    id: button

    property var window

    readonly property bool wanted: bar.drives.drives.length > 0

    name: "drives"
    visible: wanted
    active: bar.popup === "drives"
    implicitWidth: height

    Kirigami.Icon {
        anchors.centerIn: parent
        width: 16
        height: 16
        source: "drive-removable-media"
    }

    onClicked: {
        const r = button.windowRect();
        bar.openPanel("drives", button.window.targetScreen, r.x, r.y, r.width, r.height);
    }
}
