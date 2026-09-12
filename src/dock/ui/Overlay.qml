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
    property string mode: "menu"          // menu | stack
    property var stackEntries: []
    property string stackTitle: ""
    property string stackPath: ""
    property string stackView: "auto"
    property bool dragging: false          // an item is being dragged out of a Stack
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
        dragging = false;
        dock.menuOpen = false;
    }
    function show(kind, screen, row, x, y, w, h, edge) {
        overlay.visible = false;              // a fresh surface, on the right screen
        overlay.targetScreen = screen;
        overlay.mode = kind;
        overlay.row = row;
        overlay.anchorRect = Qt.rect(x, y, w, h);
        overlay.edge = edge;
        dock.menuOpen = true;
        overlay.visible = true;
    }
    function clamp(v, lo, hi) {
        return Math.max(lo, Math.min(hi, v));
    }
    function pushSurface() {
        if (!visible) {
            return;
        }
        if (mode === "stack") {
            // while a file is dragged out, only the Stack takes input, so the
            // drop can land on whatever is underneath
            dock.updateSurface(overlay, dragging ? [stack.inputRect] : [], stack.blurRect, stack.blurRadius);
        } else {
            dock.updateSurface(overlay, [], Qt.rect(menu.x, menu.y, menu.width, menu.height), menu.radius);
        }
    }
    onDraggingChanged: Qt.callLater(pushSurface)
    onModeChanged: Qt.callLater(pushSurface)

    Connections {
        target: dock
        function onMenuRequested(entries, row, screen, x, y, w, h, edge) {
            overlay.entries = entries;
            menu.currentIndex = -1;
            overlay.show("menu", screen, row, x, y, w, h, edge);
            menu.forceActiveFocus();
        }
        function onStackRequested(entries, title, path, view, row, screen, x, y, w, h, edge) {
            overlay.stackEntries = entries;
            overlay.stackTitle = title;
            overlay.stackPath = path;
            overlay.stackView = view;
            overlay.show("stack", screen, row, x, y, w, h, edge);
            stack.forceActiveFocus();
        }
    }

    onVisibleChanged: Qt.callLater(pushSurface)

    MouseArea {
        anchors.fill: parent
        acceptedButtons: Qt.AllButtons
        onPressed: overlay.close()
    }

    StackPopup {
        id: stack
        anchors.fill: parent
        visible: overlay.mode === "stack"
        entries: overlay.stackEntries
        title: overlay.stackTitle
        view: overlay.stackView
        edge: overlay.edge
        anchorRect: overlay.anchorRect
        onOpened: url => {
            overlay.close();
            dock.openUrl(url);
        }
        onOpenFolder: {
            overlay.close();
            dock.openStackFolder(overlay.stackPath);
        }
        onDismissed: overlay.close()
        onDragStarted: overlay.dragging = true
        onDragFinished: overlay.close()
        onBlurRectChanged: Qt.callLater(overlay.pushSurface)
    }

    DockMenu {
        id: menu
        visible: overlay.mode === "menu"
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
