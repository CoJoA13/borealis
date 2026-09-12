/*
    One place in the dock: an app, the trash, or a divider.
    SPDX-License-Identifier: GPL-3.0-or-later
*/
import QtQuick
import org.kde.kirigami as Kirigami

Item {
    id: item

    required property var host   // the DockView
    required property int index
    required property string kind
    required property string key
    required property string appId
    required property string name
    required property string icon
    required property bool pinned
    required property var windows
    required property int windowCount
    required property bool active
    required property bool attention
    required property bool launching
    required property bool hasEntry

    readonly property real span: kind === "divider" ? host.dividerSpan : host.iconSize
    property bool settled: false
    property real restX: host.restStart + (host.offsets[index] !== undefined ? host.offsets[index] : 0)
    Behavior on restX {
        enabled: item.settled && host.motion && !item.dragged
        NumberAnimation { duration: 240 * host.anim; easing.type: Easing.OutCubic }
    }
    readonly property real liveA: host.live(restX)
    readonly property real liveB: host.live(restX + span)
    readonly property real size: liveB - liveA
    readonly property bool dragged: host.dragging && host.dragRow === index
    readonly property bool hovered: host.hoveredDock && host.pointer >= liveA && host.pointer < liveB

    x: dragged ? host.dragX - width / 2 : liveA
    y: kind === "divider" ? host.shelfY
        : dragged ? host.dragY - height / 2
        : host.shelfY + host.thickness - host.padding - size
    width: size
    height: kind === "divider" ? host.thickness : size
    z: dragged ? 10 : hovered ? 2 : 0

    scale: settled ? 1 : 0.3
    opacity: settled ? 1 : 0
    Behavior on scale {
        enabled: host.motion
        NumberAnimation { duration: 260 * host.anim; easing.type: Easing.OutBack }
    }
    Behavior on opacity {
        enabled: host.motion
        NumberAnimation { duration: 200 * host.anim }
    }
    Component.onCompleted: Qt.callLater(() => { item.settled = true; })

    Rectangle {
        visible: item.kind === "divider"
        anchors.centerIn: parent
        width: 1
        height: host.iconSize * 0.7
        color: Qt.rgba(Kirigami.Theme.textColor.r, Kirigami.Theme.textColor.g, Kirigami.Theme.textColor.b, 0.28)
    }

    Kirigami.Icon {
        id: glyph
        visible: item.kind !== "divider"
        anchors.fill: parent
        source: item.kind === "trash" ? (dock.trashFull ? "user-trash-full" : "user-trash") : item.icon
        roundToIconSize: false          // magnified sizes are in between the standard ones
        opacity: item.dragged && host.removing ? 0.4 : 1
        transform: Translate { id: lift }
    }

    // a bounce while an app starts, and a slower one when it wants attention
    SequentialAnimation {
        running: host.cfg.bounce && host.motion && item.kind === "app" && (item.launching || item.attention)
        loops: Animation.Infinite
        NumberAnimation {
            target: lift; property: "y"; to: -host.iconSize * 0.5
            duration: 280 * host.anim; easing.type: Easing.OutQuad
        }
        NumberAnimation {
            target: lift; property: "y"; to: 0
            duration: 380 * host.anim; easing.type: Easing.OutBounce
        }
        PauseAnimation { duration: item.launching ? 40 : 900 }
        onStopped: lift.y = 0
    }

    Rectangle {
        id: dot
        readonly property bool line: host.cfg.indicator === "line"
        visible: item.kind === "app" && item.windowCount > 0 && host.cfg.indicator !== "none" && !item.dragged
        width: line ? Math.max(10, host.iconSize * 0.3) : 5
        height: line ? 3 : 5
        radius: height / 2
        anchors.horizontalCenter: parent.horizontalCenter
        y: item.height + Math.max(1, (host.padding - height) / 2)
        color: item.active ? Kirigami.Theme.highlightColor
                           : Qt.rgba(Kirigami.Theme.textColor.r, Kirigami.Theme.textColor.g,
                                     Kirigami.Theme.textColor.b, 0.6)
    }

    Rectangle {
        id: label
        Kirigami.Theme.colorSet: Kirigami.Theme.Tooltip
        Kirigami.Theme.inherit: false
        readonly property real outward: host.vertical ? width : height
        visible: host.cfg.labels && item.kind !== "divider" && !host.hidden
            && ((item.hovered && !host.dragging) || (item.dragged && host.removing))
        width: labelText.implicitWidth + 22
        height: labelText.implicitHeight + 10
        radius: height / 2
        rotation: host.edge === "left" ? -90 : host.edge === "right" ? 90 : 0
        x: (item.width - width) / 2
        y: -12 - outward / 2 - height / 2
        color: Qt.rgba(Kirigami.Theme.backgroundColor.r, Kirigami.Theme.backgroundColor.g,
                       Kirigami.Theme.backgroundColor.b, 0.92)
        border.width: 1
        border.color: Qt.rgba(Kirigami.Theme.textColor.r, Kirigami.Theme.textColor.g,
                              Kirigami.Theme.textColor.b, 0.12)

        Text {
            id: labelText
            anchors.centerIn: parent
            text: item.dragged && host.removing ? qsTr("Remove") : item.kind === "trash" ? qsTr("Trash") : item.name
            color: Kirigami.Theme.textColor
            font.pointSize: Kirigami.Theme.defaultFont.pointSize
        }
    }

    TapHandler {
        enabled: item.kind !== "divider"
        acceptedButtons: Qt.LeftButton | Qt.MiddleButton | Qt.RightButton
        onTapped: (eventPoint, button) => {
            if (button === Qt.RightButton) {
                host.openMenu(item);
            } else if (button === Qt.MiddleButton) {
                dock.middleClick(item.index);
            } else {
                dock.click(item.index);
            }
        }
    }
    TapHandler {
        enabled: item.kind === "divider"
        acceptedButtons: Qt.RightButton
        onTapped: host.openMenu(item)
    }
    WheelHandler {
        enabled: item.kind === "app"
        property real turned: 0
        onWheel: event => {
            turned += event.angleDelta.y;
            if (Math.abs(turned) >= 120) {
                dock.scroll(item.index, turned > 0 ? -1 : 1);
                turned = 0;
            }
        }
    }
    DragHandler {
        target: null
        enabled: item.kind === "app"
        dragThreshold: 10
        onActiveChanged: active ? host.beginDrag(item) : host.endDrag(item)
        onCentroidChanged: if (active) {
            host.moveDrag(item, centroid.scenePosition);
        }
    }
}
