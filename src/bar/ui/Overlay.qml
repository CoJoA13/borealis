/*
    Where the bar's popups open: a transparent layer-shell surface over the
    whole screen, shown only while one is up, so a click anywhere else closes
    it. (Qt's own popup windows don't work on layer-shell surfaces.)
    While an app's menu is open, hovering another of its titles switches to it.
    SPDX-License-Identifier: GPL-3.0-or-later
*/
import QtQuick
import org.kde.layershell as LayerShell

Window {
    id: overlay

    property var notices: null
    property var status: null
    property var targetScreen: null
    property string mode: ""            // menu | clock | controls | drives | confirm
    property string source: ""          // what a menu belongs to: system, app:<key>, tray:<key>
    property var entries: []
    property rect anchorRect: Qt.rect(0, 0, 0, 0)
    property var confirm: ({title: "", text: "", label: "", action: ""})
    property var titles: []
    property int commitTick: 0

    title: "Bar popup"
    color: "transparent"
    visible: false
    width: 800
    height: 600

    LayerShell.Window.scope: "bar"
    LayerShell.Window.layer: LayerShell.Window.LayerOverlay
    LayerShell.Window.screen: targetScreen
    LayerShell.Window.anchors: LayerShell.Window.AnchorTop | LayerShell.Window.AnchorBottom
        | LayerShell.Window.AnchorLeft | LayerShell.Window.AnchorRight
    LayerShell.Window.exclusionZone: -1
    LayerShell.Window.keyboardInteractivity: LayerShell.Window.KeyboardInteractivityExclusive

    readonly property Item current: mode === "menu" ? menu : mode === "clock" ? clockPanel
        : mode === "controls" ? controlCenter : mode === "drives" ? drivesPopup
        : mode === "confirm" ? confirmDialog : null

    function open(kind, name, screen, x, y, w, h) {
        const reuse = overlay.visible && overlay.targetScreen === screen;
        if (!reuse) {
            overlay.visible = false;                 // a fresh surface, on the right screen
            overlay.targetScreen = screen;
        }
        overlay.mode = kind;
        overlay.anchorRect = Qt.rect(x, y, w, h);
        bar.setPopup(name);
        overlay.visible = true;
        Qt.callLater(overlay.focusCurrent);
        Qt.callLater(overlay.pushSurface);
    }
    function close() {
        if (!overlay.visible) {
            return;
        }
        overlay.visible = false;
        overlay.mode = "";
        bar.setPopup("");
    }
    function focusCurrent() {
        if (overlay.current) {
            overlay.current.forceActiveFocus();
        }
    }
    // under the bar button a popup belongs to, and on screen
    function placeX(w, align) {
        const r = overlay.anchorRect;
        const left = align === "left" ? r.x : align === "right" ? r.x + r.width - w : r.x + r.width / 2 - w / 2;
        return Math.max(8, Math.min(overlay.width - w - 8, left));
    }
    function placeY() {
        return overlay.anchorRect.y + overlay.anchorRect.height + 6;
    }
    function pushSurface() {
        if (!overlay.visible || !overlay.current) {
            return;
        }
        const c = overlay.current;
        bar.updateSurface(overlay, [], Qt.rect(c.x, c.y, c.width, c.height), c.radius !== undefined ? c.radius : 12);
    }
    onVisibleChanged: Qt.callLater(pushSurface)
    onModeChanged: Qt.callLater(pushSurface)

    Connections {
        target: bar
        function onMenuRequested(entries, source, screen, x, y, w, h) {
            overlay.entries = entries;
            overlay.source = source;
            overlay.titles = source.startsWith("app:") ? bar.menuTitleRects(screen ? screen.name : "") : [];
            overlay.open("menu", source, screen, x, y, w, h);
            menu.reset();
        }
        function onSubmenuReady(source, key, entries) {
            if (source === overlay.source) {
                menu.fill(key, entries);
            }
        }
        function onPanelRequested(kind, screen, x, y, w, h) {
            overlay.open(kind, kind, screen, x, y, w, h);
            if (kind === "clock" && overlay.notices) {
                overlay.notices.markRead();
            }
        }
        function onConfirmRequested(title, text, label, action) {
            overlay.confirm = {title: title, text: text, label: label, action: action};
            overlay.open("confirm", "confirm", overlay.targetScreen || Qt.application.screens[0], 0, 0, 0, 0);
        }
        function onCloseRequested() {
            overlay.close();
        }
    }

    MouseArea {
        anchors.fill: parent
        acceptedButtons: Qt.AllButtons
        onPressed: overlay.close()
    }

    // an app's other menu titles: hovering one switches to its menu
    Repeater {
        model: overlay.mode === "menu" ? overlay.titles : []
        delegate: MouseArea {
            required property var modelData
            property bool wasOpen: false
            x: modelData.x
            y: modelData.y
            width: modelData.width
            height: modelData.height
            hoverEnabled: true
            acceptedButtons: Qt.AllButtons
            onEntered: {
                wasOpen = overlay.source === "app:" + modelData.key;
                if (!wasOpen) {
                    bar.openAppMenu(modelData.key, overlay.targetScreen, x, y, width, height);
                }
            }
            onPressed: if (wasOpen) {
                overlay.close();
            }
        }
    }

    BarMenu {
        id: menu
        visible: overlay.mode === "menu"
        entries: overlay.entries
        x: overlay.placeX(width, "left")
        y: overlay.placeY()
        maxRight: overlay.width
        onTriggered: key => {
            const source = overlay.source;
            overlay.close();
            bar.triggerMenu(source, key);
        }
        onSubmenuWanted: key => bar.openSubmenu(overlay.source, key)
        onDismissed: overlay.close()
        onXChanged: Qt.callLater(overlay.pushSurface)
        onWidthChanged: Qt.callLater(overlay.pushSurface)
        onHeightChanged: Qt.callLater(overlay.pushSurface)
    }

    ClockPanel {
        id: clockPanel
        visible: overlay.mode === "clock"
        notices: overlay.notices
        x: overlay.placeX(width, "center")
        y: overlay.placeY()
        onDismissed: overlay.close()
        onXChanged: Qt.callLater(overlay.pushSurface)
        onHeightChanged: Qt.callLater(overlay.pushSurface)
    }

    ControlCenter {
        id: controlCenter
        visible: overlay.mode === "controls"
        status: overlay.status
        notices: overlay.notices
        x: overlay.placeX(width, "right")
        y: overlay.placeY()
        onDismissed: overlay.close()
        onXChanged: Qt.callLater(overlay.pushSurface)
        onHeightChanged: Qt.callLater(overlay.pushSurface)
    }

    DrivesPopup {
        id: drivesPopup
        visible: overlay.mode === "drives"
        x: overlay.placeX(width, "right")
        y: overlay.placeY()
        onDismissed: overlay.close()
        onXChanged: Qt.callLater(overlay.pushSurface)
        onHeightChanged: Qt.callLater(overlay.pushSurface)
    }

    ConfirmDialog {
        id: confirmDialog
        visible: overlay.mode === "confirm"
        title: overlay.confirm.title
        text: overlay.confirm.text
        label: overlay.confirm.label
        x: (overlay.width - width) / 2
        y: Math.max(60, (overlay.height - height) / 3)
        onAccepted: {
            const action = overlay.confirm.action;
            overlay.close();
            bar.confirmed(action);
        }
        onDismissed: overlay.close()
    }

    Rectangle {
        width: 1
        height: 1
        color: overlay.commitTick % 2 ? "#01000000" : "#02000000"
    }
}
