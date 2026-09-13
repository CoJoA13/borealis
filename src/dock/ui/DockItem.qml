/*
    One place in the dock: an app, Launchpad, a widget, a Stack, the trash,
    or a divider.
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
    required property int badge
    required property real progress
    required property string stackPath
    required property int stackCount
    required property var preview
    required property string display
    required property string widget
    required property string widgetStyle

    // a Stack shows its newest items piled up; an empty one (or "folder") its icon
    readonly property bool piled: kind === "stack" && display === "stack" && preview.length > 0
    // Launchpad and the widgets draw themselves instead of showing a themed icon
    readonly property bool drawn: kind === "launchpad" || kind === "widget"
    // this app's window previews are showing
    readonly property bool previewing: dock.previewVisible && dock.previewRow === index && host.previewMine

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
        visible: item.kind !== "divider" && !item.piled && !item.drawn
        anchors.fill: parent
        source: item.kind === "trash" ? (dock.trashFull ? "user-trash-full" : "user-trash") : item.icon
        roundToIconSize: false          // magnified sizes are in between the standard ones
        opacity: item.dragged && host.removing ? 0.4 : 1
        transform: Translate { id: lift }
    }

    LaunchpadGlyph {
        visible: item.kind === "launchpad"
        anchors.fill: parent
        transform: Translate { y: lift.y }
    }

    Loader {
        id: widgetView
        active: item.kind === "widget"
        anchors.fill: parent
        sourceComponent: item.widget === "clock" ? clockWidget
            : item.widget === "battery" ? batteryWidget
            : mediaWidget
        transform: Translate { y: lift.y }
    }
    Component {
        id: clockWidget
        ClockWidget {
            style: item.widgetStyle || "analog"
        }
    }
    Component {
        id: batteryWidget
        BatteryWidget {}
    }
    Component {
        id: mediaWidget
        MediaWidget {}
    }

    Item {
        id: pile
        visible: item.piled
        anchors.fill: parent
        transform: Translate { y: lift.y }

        Repeater {
            model: item.piled ? item.preview.length : 0
            delegate: Item {
                required property int index
                // drawn oldest first, so the newest ends up on top
                readonly property int level: item.preview.length - 1 - index
                readonly property var entry: item.preview[level]
                width: pile.width * 0.78
                height: width
                anchors.centerIn: parent
                anchors.verticalCenterOffset: -level * pile.height * 0.06
                rotation: level === 0 ? 0 : (level % 2 ? -8 : 7)

                Rectangle {
                    anchors.fill: parent
                    visible: parent.entry.image
                    radius: width * 0.12
                    color: "white"
                    Image {
                        anchors.fill: parent
                        anchors.margins: parent.width * 0.06
                        source: parent.visible ? parent.parent.entry.url : ""
                        sourceSize.width: 128
                        sourceSize.height: 128
                        fillMode: Image.PreserveAspectCrop
                        asynchronous: true
                    }
                }
                Kirigami.Icon {
                    anchors.fill: parent
                    visible: !parent.entry.image
                    source: parent.entry.icon
                    roundToIconSize: false
                }
            }
        }
    }

    // a count an app publishes for its icon (unread mail, downloads left…)
    Rectangle {
        id: badgeBubble
        visible: item.kind === "app" && item.badge > 0
        height: Math.max(16, item.width * 0.36)
        width: Math.max(height, badgeText.implicitWidth + height * 0.55)
        radius: height / 2
        x: item.width - width * 0.8
        y: -height * 0.2
        color: "#e5484d"
        border.width: Math.max(1, height * 0.08)
        border.color: Qt.rgba(1, 1, 1, 0.85)
        transform: Translate { y: lift.y }

        Text {
            id: badgeText
            anchors.centerIn: parent
            text: item.badge > 99 ? "99+" : String(item.badge)
            color: "white"
            font.bold: true
            font.pixelSize: Math.round(badgeBubble.height * 0.6)
        }
    }

    // and its progress (a download, a copy)
    Rectangle {
        visible: item.kind === "app" && item.progress >= 0
        x: item.width * 0.12
        width: item.width * 0.76
        height: Math.max(4, item.width * 0.09)
        y: item.height - height - item.width * 0.05
        radius: height / 2
        color: Qt.rgba(0, 0, 0, 0.5)
        border.width: 1
        border.color: Qt.rgba(1, 1, 1, 0.25)
        transform: Translate { y: lift.y }

        Rectangle {
            width: Math.max(parent.height, parent.width * item.progress)
            height: parent.height
            radius: parent.radius
            color: Kirigami.Theme.highlightColor
        }
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
        visible: host.cfg.labels && item.kind !== "divider" && !host.hidden && !item.previewing
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
            text: item.dragged && host.removing ? qsTr("Remove")
                : item.kind === "trash" ? qsTr("Trash")
                : item.kind === "widget" && widgetView.item ? widgetView.item.label
                : item.name
            textFormat: Text.PlainText
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
            } else if (item.kind === "stack") {
                host.openStack(item);
            } else if (item.kind === "launchpad") {
                dock.toggleLaunchpadFrom(host.window);
            } else if (item.kind === "widget" && item.widget === "clock") {
                host.openCalendar(item);
            } else if (item.kind === "widget" && item.widget === "battery") {
                host.openMenu(item);
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
