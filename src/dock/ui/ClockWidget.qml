/*
    The dock's clock: an analog face, or the time in figures with the day
    beneath. It wakes once a minute, so the dock isn't redrawn every second.
    SPDX-License-Identifier: GPL-3.0-or-later
*/
import QtQuick
import org.kde.kirigami as Kirigami

Item {
    id: clock

    property string style: "analog"
    property var now: new Date()
    readonly property string label: Qt.formatDate(now, Locale.LongFormat)
    // the locale's short time, without seconds or AM/PM (the day sits beneath)
    readonly property string timeFormat: Qt.locale().timeFormat(Locale.ShortFormat)
        .replace(/:ss/, "").replace(/\s*[aA][pP]?$/, "").replace(/\s*[aA][pP]?\s/, " ")

    Kirigami.Theme.colorSet: Kirigami.Theme.View
    Kirigami.Theme.inherit: false

    Timer {
        running: true
        interval: 60000 - (Date.now() % 60000) + 30
        onTriggered: {
            clock.now = new Date();
            interval = 60000 - (Date.now() % 60000) + 30;
            restart();
        }
    }

    // ---- analog -----------------------------------------------------------------
    Item {
        id: face
        visible: clock.style !== "digital"
        anchors.fill: parent
        readonly property real hours: clock.now.getHours() % 12 + clock.now.getMinutes() / 60
        readonly property real minutes: clock.now.getMinutes()

        Rectangle {
            id: dial
            anchors.fill: parent
            anchors.margins: parent.width * 0.05
            radius: width / 2
            gradient: Gradient {
                GradientStop { position: 0.0; color: Qt.lighter(Kirigami.Theme.backgroundColor, 1.12) }
                GradientStop { position: 1.0; color: Kirigami.Theme.backgroundColor }
            }
            border.width: Math.max(1.5, width * 0.05)
            border.color: Kirigami.Theme.highlightColor
        }

        Repeater {
            model: 12
            Item {
                required property int index
                x: dial.x
                y: dial.y
                width: dial.width
                height: dial.height
                rotation: index * 30
                Rectangle {
                    anchors.horizontalCenter: parent.horizontalCenter
                    y: parent.height * 0.11
                    width: Math.max(1, parent.width * (parent.index % 3 === 0 ? 0.05 : 0.03))
                    height: parent.height * (parent.index % 3 === 0 ? 0.1 : 0.06)
                    radius: width / 2
                    color: Kirigami.Theme.textColor
                    opacity: parent.index % 3 === 0 ? 0.85 : 0.45
                }
            }
        }

        Rectangle {
            id: hourHand
            width: Math.max(2, dial.width * 0.075)
            height: dial.height * 0.3
            radius: width / 2
            antialiasing: true
            color: Kirigami.Theme.textColor
            x: dial.x + (dial.width - width) / 2
            y: dial.y + dial.height / 2 - height + width / 2
            transform: Rotation {
                origin.x: hourHand.width / 2
                origin.y: hourHand.height - hourHand.width / 2
                angle: face.hours * 30
            }
        }
        Rectangle {
            id: minuteHand
            width: Math.max(1.5, dial.width * 0.05)
            height: dial.height * 0.42
            radius: width / 2
            antialiasing: true
            color: Kirigami.Theme.highlightColor
            x: dial.x + (dial.width - width) / 2
            y: dial.y + dial.height / 2 - height + width / 2
            transform: Rotation {
                origin.x: minuteHand.width / 2
                origin.y: minuteHand.height - minuteHand.width / 2
                angle: face.minutes * 6
            }
        }
        Rectangle {
            width: dial.width * 0.12
            height: width
            radius: width / 2
            anchors.centerIn: dial
            color: Kirigami.Theme.highlightColor
            border.width: Math.max(1, width * 0.2)
            border.color: Kirigami.Theme.backgroundColor
        }
    }

    // ---- digital ------------------------------------------------------------------
    Rectangle {
        id: plate
        visible: clock.style === "digital"
        anchors.fill: parent
        anchors.margins: parent.width * 0.05
        radius: width * 0.24
        color: Kirigami.Theme.backgroundColor
        border.width: Math.max(1, width * 0.03)
        border.color: Qt.rgba(Kirigami.Theme.textColor.r, Kirigami.Theme.textColor.g, Kirigami.Theme.textColor.b, 0.18)

        Column {
            anchors.centerIn: parent
            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: Qt.formatTime(clock.now, clock.timeFormat)
                font.pixelSize: Math.max(8, plate.height * 0.3)
                font.weight: Font.DemiBold
                color: Kirigami.Theme.textColor
            }
            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: Qt.formatDate(clock.now, "ddd d")
                font.pixelSize: Math.max(6, plate.height * 0.17)
                color: Kirigami.Theme.highlightColor
            }
        }
    }
}
