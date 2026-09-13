/*
    A Control Center slider: an icon button (mute, for sound), a wide track,
    and an arrow to its page when it has one.
    SPDX-License-Identifier: GPL-3.0-or-later
*/
import QtQuick
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

RowLayout {
    id: row

    property string iconName
    property string tip
    property real value: 0
    property bool dimmed: false
    property bool hasDetails: false
    signal moved(real value)
    signal iconClicked()
    signal detailsRequested()

    readonly property color fg: Kirigami.Theme.textColor
    readonly property real shown: drag.pressed ? drag.dragValue : Math.max(0, Math.min(1, value))

    spacing: 10

    IconButton {
        iconName: row.iconName
        tip: row.tip
        size: 32
        onClicked: row.iconClicked()
    }

    Item {
        id: track
        Layout.fillWidth: true
        implicitHeight: 32
        opacity: row.dimmed ? 0.5 : 1
        Accessible.role: Accessible.Slider
        Accessible.name: row.tip

        Rectangle {
            anchors.verticalCenter: parent.verticalCenter
            width: parent.width
            height: 6
            radius: 3
            color: Qt.rgba(row.fg.r, row.fg.g, row.fg.b, 0.15)
        }
        Rectangle {
            anchors.verticalCenter: parent.verticalCenter
            width: parent.width * row.shown
            height: 6
            radius: 3
            color: Kirigami.Theme.highlightColor
        }
        Rectangle {
            anchors.verticalCenter: parent.verticalCenter
            x: (parent.width - width) * row.shown
            width: 18
            height: 18
            radius: 9
            color: Kirigami.Theme.backgroundColor
            border.width: 1
            border.color: Qt.rgba(row.fg.r, row.fg.g, row.fg.b, 0.3)
        }
        MouseArea {
            id: drag
            property real dragValue: 0
            anchors.fill: parent
            cursorShape: Qt.PointingHandCursor
            function update(x) {
                dragValue = Math.max(0, Math.min(1, x / width));
                row.moved(dragValue);
            }
            onPressed: mouse => update(mouse.x)
            onPositionChanged: mouse => update(mouse.x)
        }
        WheelHandler {
            onWheel: event => row.moved(Math.max(0, Math.min(1, row.value + (event.angleDelta.y > 0 ? 0.05 : -0.05))))
        }
    }

    IconButton {
        visible: row.hasDetails
        iconName: "go-next"
        tip: qsTr("More")
        size: 28
        onClicked: row.detailsRequested()
    }
}
