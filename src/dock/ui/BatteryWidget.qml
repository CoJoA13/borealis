/*
    The battery: its charge drawn to scale, a bolt while plugged in, the
    percentage beneath. Red when it runs low.
    SPDX-License-Identifier: GPL-3.0-or-later
*/
import QtQuick
import QtQuick.Shapes
import org.kde.kirigami as Kirigami

Item {
    id: widget

    readonly property var battery: dock.battery
    readonly property string label: qsTr("Battery %1% · %2").arg(battery.percent).arg(battery.status)
    readonly property bool low: battery.percent <= 15 && !battery.pluggedIn

    Kirigami.Theme.colorSet: Kirigami.Theme.View
    Kirigami.Theme.inherit: false

    Rectangle {
        id: plate
        anchors.fill: parent
        anchors.margins: parent.width * 0.05
        radius: width * 0.24
        color: Kirigami.Theme.backgroundColor
        border.width: Math.max(1, width * 0.03)
        border.color: Qt.rgba(Kirigami.Theme.textColor.r, Kirigami.Theme.textColor.g, Kirigami.Theme.textColor.b, 0.18)
    }

    Rectangle {
        id: body
        width: plate.width * 0.6
        height: plate.height * 0.34
        x: plate.x + (plate.width - width - cap.width) / 2
        y: plate.y + plate.height * 0.2
        radius: height * 0.26
        color: "transparent"
        border.width: Math.max(1.2, plate.width * 0.045)
        border.color: widget.low ? "#e5484d" : Kirigami.Theme.textColor

        Rectangle {
            readonly property real inset: body.border.width + Math.max(1, body.height * 0.08)
            x: inset
            y: inset
            height: body.height - 2 * inset
            width: Math.max(0, (body.width - 2 * inset) * Math.min(100, widget.battery.percent) / 100)
            radius: Math.max(0, body.radius - inset / 2)
            color: widget.low ? "#e5484d" : widget.battery.pluggedIn ? "#3ecf8e" : Kirigami.Theme.highlightColor
        }
    }

    Rectangle {
        id: cap
        width: Math.max(2, plate.width * 0.05)
        height: body.height * 0.42
        x: body.x + body.width + Math.max(1, plate.width * 0.012)
        y: body.y + (body.height - height) / 2
        radius: width / 2
        color: body.border.color
    }

    Shape {
        id: bolt
        visible: widget.battery.pluggedIn
        width: body.height * 0.9
        height: body.height * 1.35
        x: body.x + (body.width - width) / 2
        y: body.y + (body.height - height) / 2
        preferredRendererType: Shape.CurveRenderer
        ShapePath {
            fillColor: "white"
            strokeColor: Qt.rgba(0, 0, 0, 0.6)
            strokeWidth: Math.max(1, bolt.width * 0.07)
            joinStyle: ShapePath.RoundJoin
            startX: bolt.width * 0.62
            startY: 0
            PathLine { x: bolt.width * 0.08; y: bolt.height * 0.57 }
            PathLine { x: bolt.width * 0.46; y: bolt.height * 0.57 }
            PathLine { x: bolt.width * 0.36; y: bolt.height }
            PathLine { x: bolt.width * 0.92; y: bolt.height * 0.4 }
            PathLine { x: bolt.width * 0.54; y: bolt.height * 0.4 }
            PathLine { x: bolt.width * 0.62; y: 0 }
        }
    }

    Text {
        anchors.horizontalCenter: plate.horizontalCenter
        y: body.y + body.height + plate.height * 0.07
        text: widget.battery.percent + "%"
        font.pixelSize: Math.max(7, plate.height * 0.24)
        font.weight: Font.DemiBold
        color: widget.low ? "#e5484d" : Kirigami.Theme.textColor
    }
}
