/*
    Anything clickable in the bar: highlights on hover and while its popup is
    open, and tells the bar where it is (menus open under it, and switching
    between an app's menus needs every title's place).
    SPDX-License-Identifier: GPL-3.0-or-later
*/
import QtQuick
import org.kde.kirigami as Kirigami

Item {
    id: button

    property string name
    property bool active: false
    readonly property bool hovered: hover.hovered
    readonly property color fg: Kirigami.Theme.textColor
    signal clicked(int mouseButton)
    signal scrolled(int delta, bool horizontal)

    function windowRect() {
        const p = button.mapToItem(null, 0, 0);
        return Qt.rect(p.x, p.y, button.width, button.height);
    }
    function report() {
        const w = button.Window.window;
        if (button.name && w && w.targetScreen && button.visible) {
            bar.placeButton(button.name, w.targetScreen.name, button.windowRect());
        }
    }

    onXChanged: Qt.callLater(report)
    onWidthChanged: Qt.callLater(report)
    onVisibleChanged: Qt.callLater(report)
    Component.onCompleted: Qt.callLater(report)
    Connections {
        target: button.Window.window
        ignoreUnknownSignals: true
        function onLayoutChanged() {
            Qt.callLater(button.report);
        }
    }

    Rectangle {
        anchors.fill: parent
        anchors.topMargin: 3
        anchors.bottomMargin: 3
        radius: 7
        color: button.active ? Qt.rgba(button.fg.r, button.fg.g, button.fg.b, 0.18)
             : hover.hovered ? Qt.rgba(button.fg.r, button.fg.g, button.fg.b, 0.10) : "transparent"
        Behavior on color {
            ColorAnimation {
                duration: 90
            }
        }
    }

    HoverHandler {
        id: hover
        onHoveredChanged: if (hovered) {
            button.report();
        }
    }
    TapHandler {
        acceptedButtons: Qt.LeftButton | Qt.RightButton | Qt.MiddleButton
        onTapped: (point, mouseButton) => button.clicked(mouseButton)
    }
    WheelHandler {
        onWheel: event => button.scrolled(event.angleDelta.y !== 0 ? event.angleDelta.y : event.angleDelta.x,
                                          event.angleDelta.y === 0)
    }
}
