/*
    One dock surface: a layer-shell strip along a screen edge, transparent but
    for the shelf, and deep enough for magnified icons to rise out of it.
    SPDX-License-Identifier: GPL-3.0-or-later
*/
import QtQuick
import org.kde.layershell as LayerShell

Window {
    id: win

    property var targetScreen: null
    readonly property var cfg: dock.settings.values
    readonly property string edge: cfg.position
    readonly property bool vertical: edge !== "bottom"
    readonly property int thickness: cfg.iconSize + 2 * cfg.padding
    // room outside the shelf for magnified icons, bounces and name labels
    readonly property int headroom: Math.ceil(cfg.iconSize * Math.max(0.5, cfg.zoom - 1))
        + (cfg.labels ? (vertical ? 220 : 44) : 0) + 8
    // while an icon is dragged the surface grows, so it can be carried off the dock
    readonly property int depth: cfg.margin + thickness + headroom + (dockView.dragging ? 240 : 0)
    property int commitTick: 0

    title: "Dock"
    color: "transparent"
    visible: true
    width: vertical ? depth : 800
    height: vertical ? 600 : depth

    LayerShell.Window.scope: "dock"
    LayerShell.Window.layer: LayerShell.Window.LayerTop
    LayerShell.Window.screen: targetScreen
    LayerShell.Window.wantsToBeOnActiveScreen: cfg.screen === "follow"
    LayerShell.Window.keyboardInteractivity: LayerShell.Window.KeyboardInteractivityNone
    LayerShell.Window.anchors: edge === "left"
        ? (LayerShell.Window.AnchorLeft | LayerShell.Window.AnchorTop | LayerShell.Window.AnchorBottom)
        : edge === "right"
            ? (LayerShell.Window.AnchorRight | LayerShell.Window.AnchorTop | LayerShell.Window.AnchorBottom)
            : (LayerShell.Window.AnchorBottom | LayerShell.Window.AnchorLeft | LayerShell.Window.AnchorRight)
    LayerShell.Window.exclusionZone: cfg.hide === "always" ? cfg.margin + thickness : 0

    DockView {
        id: dockView
        anchors.fill: parent
        window: win
    }

    // Input regions and blur only take effect with a commit: Python bumps this
    // after changing them, so a frame always follows
    Rectangle {
        width: 1
        height: 1
        color: win.commitTick % 2 ? "#01000000" : "#02000000"
    }
}
