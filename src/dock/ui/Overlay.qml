/*
    Where the dock's menus open: a transparent layer-shell surface over the
    whole screen, shown only while a menu is up, so a click anywhere outside
    the menu closes it. (Qt's own popup windows don't work on layer-shell
    surfaces: they turn into stray surfaces of their own.)
    SPDX-License-Identifier: GPL-3.0-or-later
*/
import QtQuick
import org.kde.layershell as LayerShell

Window {
    id: overlay

    property var targetScreen: null
    property var entries: []
    property int row: -1
    property rect anchorRect: Qt.rect(0, 0, 0, 0)
    property string edge: "bottom"
    property int commitTick: 0

    title: "Dock menu"
    color: "transparent"
    visible: false
    width: 800
    height: 600

    LayerShell.Window.scope: "dock"
    LayerShell.Window.layer: LayerShell.Window.LayerOverlay
    LayerShell.Window.screen: targetScreen
    LayerShell.Window.anchors: LayerShell.Window.AnchorTop | LayerShell.Window.AnchorBottom
        | LayerShell.Window.AnchorLeft | LayerShell.Window.AnchorRight
    LayerShell.Window.exclusionZone: -1
    LayerShell.Window.keyboardInteractivity: LayerShell.Window.KeyboardInteractivityExclusive

    function close() {
        visible = false;
        dock.menuOpen = false;
    }
    function clamp(v, lo, hi) {
        return Math.max(lo, Math.min(hi, v));
    }
    function pushSurface() {
        if (visible) {
            dock.updateSurface(overlay, [], Qt.rect(menu.x, menu.y, menu.width, menu.height), menu.radius);
        }
    }

    Connections {
        target: dock
        function onMenuRequested(entries, row, screen, x, y, w, h, edge) {
            overlay.visible = false;              // a fresh surface, on the right screen
            overlay.targetScreen = screen;
            overlay.entries = entries;
            overlay.row = row;
            overlay.anchorRect = Qt.rect(x, y, w, h);
            overlay.edge = edge;
            menu.currentIndex = -1;
            dock.menuOpen = true;
            overlay.visible = true;
            menu.forceActiveFocus();
        }
    }

    onVisibleChanged: Qt.callLater(pushSurface)

    MouseArea {
        anchors.fill: parent
        acceptedButtons: Qt.AllButtons
        onPressed: overlay.close()
    }

    DockMenu {
        id: menu
        entries: overlay.entries
        x: overlay.clamp(overlay.edge === "bottom" ? overlay.anchorRect.x + overlay.anchorRect.width / 2 - width / 2
                         : overlay.edge === "left" ? overlay.anchorRect.x + overlay.anchorRect.width + 14
                         : overlay.anchorRect.x - width - 14,
                         8, Math.max(8, overlay.width - width - 8))
        y: overlay.clamp(overlay.edge === "bottom" ? overlay.anchorRect.y - height - 14
                         : overlay.anchorRect.y + overlay.anchorRect.height / 2 - height / 2,
                         8, Math.max(8, overlay.height - height - 8))
        onTriggered: key => {
            const row = overlay.row;
            overlay.close();
            dock.menuTriggered(row, key);
        }
        onDismissed: overlay.close()
        onXChanged: Qt.callLater(overlay.pushSurface)
        onYChanged: Qt.callLater(overlay.pushSurface)
        onWidthChanged: Qt.callLater(overlay.pushSurface)
        onHeightChanged: Qt.callLater(overlay.pushSurface)
    }

    Rectangle {
        width: 1
        height: 1
        color: overlay.commitTick % 2 ? "#01000000" : "#02000000"
    }
}
