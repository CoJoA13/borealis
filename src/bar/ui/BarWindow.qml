/*
    One bar: a layer-shell strip across the top of a screen. It floats with a
    gap around it, and turns flush and solid while a maximized window is on
    its screen. Items sit in three zones, as the settings arrange them.
    SPDX-License-Identifier: GPL-3.0-or-later
*/
import QtQuick
import QtQuick.Layouts
import org.kde.kirigami as Kirigami
import org.kde.layershell as LayerShell

Window {
    id: win

    property var targetScreen: null
    property var notices: null
    property var status: null
    readonly property var cfg: bar.settings.values
    // a maximized or full-screen window on this screen
    readonly property bool covered: {
        const s = win.targetScreen;
        return !!s && bar.windows.covered.some(r => r.x === s.geometry.x && r.y === s.geometry.y);
    }
    readonly property bool flush: !cfg.floating || (cfg.flush && covered)
    readonly property int gap: cfg.floating ? cfg.gap : 0
    property int commitTick: 0
    // something moved the zones: the buttons tell the bar where they are now
    signal layoutChanged()

    title: "Bar"
    color: "transparent"
    visible: true
    width: 800
    height: cfg.height + gap

    LayerShell.Window.scope: "bar"
    LayerShell.Window.layer: LayerShell.Window.LayerTop
    LayerShell.Window.screen: targetScreen
    LayerShell.Window.anchors: LayerShell.Window.AnchorTop | LayerShell.Window.AnchorLeft
        | LayerShell.Window.AnchorRight
    LayerShell.Window.exclusionZone: height
    LayerShell.Window.keyboardInteractivity: LayerShell.Window.KeyboardInteractivityNone

    Kirigami.Theme.colorSet: Kirigami.Theme.Window
    Kirigami.Theme.inherit: false

    function pushSurface() {
        bar.updateSurface(win, [], Qt.rect(shelf.x, shelf.y, shelf.width, shelf.height),
                          win.cfg.blur ? shelf.radius : -1);
    }
    onWidthChanged: Qt.callLater(pushSurface)
    onVisibleChanged: Qt.callLater(pushSurface)

    Rectangle {
        id: shelf
        readonly property color bg: Kirigami.Theme.backgroundColor
        readonly property color fg: Kirigami.Theme.textColor

        x: win.flush ? 0 : win.gap
        y: win.flush ? 0 : win.gap
        width: win.width - 2 * x
        height: win.flush ? win.height : win.cfg.height
        radius: win.flush ? 0 : win.cfg.radius
        color: Qt.rgba(bg.r, bg.g, bg.b, win.covered && win.cfg.flush ? Math.max(0.94, win.cfg.opacity) : win.cfg.opacity)
        border.width: !win.flush && win.cfg.border ? 1 : 0
        border.color: Qt.rgba(fg.r, fg.g, fg.b, 0.12)

        Behavior on x {
            NumberAnimation { duration: Kirigami.Units.shortDuration; easing.type: Easing.OutCubic }
        }
        Behavior on y {
            NumberAnimation { duration: Kirigami.Units.shortDuration; easing.type: Easing.OutCubic }
        }
        Behavior on height {
            NumberAnimation { duration: Kirigami.Units.shortDuration; easing.type: Easing.OutCubic }
        }
        Behavior on radius {
            NumberAnimation { duration: Kirigami.Units.shortDuration; easing.type: Easing.OutCubic }
        }
        Behavior on color {
            ColorAnimation { duration: Kirigami.Units.shortDuration }
        }
        onXChanged: Qt.callLater(win.pushSurface)
        onYChanged: Qt.callLater(win.pushSurface)
        onHeightChanged: Qt.callLater(win.pushSurface)
        onRadiusChanged: Qt.callLater(win.pushSurface)
    }

    Item {
        id: content
        x: shelf.x + 6
        width: shelf.width - 12
        y: (win.height - win.cfg.height) / 2 + (win.flush ? 0 : win.gap / 2)
        height: win.cfg.height

        RowLayout {
            id: leftZone
            anchors.left: parent.left
            height: parent.height
            spacing: 2
            Repeater {
                model: win.cfg.left
                delegate: BarItem {
                    required property string modelData
                    name: modelData
                    window: win
                    // an app's menu titles stop where the centre (or right) zone starts
                    limit: (centerZone.width > 0 ? centerZone.x : rightZone.x) - 16
                }
            }
        }

        RowLayout {
            id: centerZone
            anchors.horizontalCenter: parent.horizontalCenter
            height: parent.height
            spacing: 2
            Repeater {
                model: win.cfg.center
                delegate: BarItem {
                    required property string modelData
                    name: modelData
                    window: win
                }
            }
        }

        RowLayout {
            id: rightZone
            anchors.right: parent.right
            height: parent.height
            spacing: 2
            Repeater {
                model: win.cfg.right
                delegate: BarItem {
                    required property string modelData
                    name: modelData
                    window: win
                }
            }
        }
    }

    // the zones move when the bar resizes or an item changes its width
    Connections {
        target: content
        function onWidthChanged() {
            win.layoutChanged();
        }
        function onYChanged() {
            win.layoutChanged();
        }
    }
    Connections {
        target: leftZone
        function onWidthChanged() {
            win.layoutChanged();
        }
    }
    Connections {
        target: centerZone
        function onXChanged() {
            win.layoutChanged();
        }
    }
    Connections {
        target: rightZone
        function onXChanged() {
            win.layoutChanged();
        }
    }

    // input regions and blur only take effect with a commit: Python bumps this
    Rectangle {
        width: 1
        height: 1
        color: win.commitTick % 2 ? "#01000000" : "#02000000"
    }
}
