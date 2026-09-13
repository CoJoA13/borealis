/*
    A month at a glance, for the dock's clock. Arrow keys or the buttons
    change the month; Escape or a click outside closes it.
    SPDX-License-Identifier: GPL-3.0-or-later
*/
import QtQuick
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

Rectangle {
    id: cal

    signal dismissed()

    property int year: 2000
    property int month: 0
    property var today: new Date()
    readonly property var locale: Qt.locale()
    readonly property real cell: 36
    readonly property color fg: Kirigami.Theme.textColor

    function reset() {
        today = new Date();
        year = today.getFullYear();
        month = today.getMonth();
    }
    function step(n) {
        const d = new Date(year, month + n, 1);
        year = d.getFullYear();
        month = d.getMonth();
    }

    Kirigami.Theme.colorSet: Kirigami.Theme.Window
    Kirigami.Theme.inherit: false

    width: 7 * cell + 28
    height: column.implicitHeight + 28
    radius: 14
    color: Qt.rgba(Kirigami.Theme.backgroundColor.r, Kirigami.Theme.backgroundColor.g,
                   Kirigami.Theme.backgroundColor.b, 0.88)
    border.width: 1
    border.color: Qt.rgba(fg.r, fg.g, fg.b, 0.14)
    focus: true

    Keys.onEscapePressed: dismissed()
    Keys.onLeftPressed: step(-1)
    Keys.onRightPressed: step(1)
    Keys.onUpPressed: step(-12)
    Keys.onDownPressed: step(12)

    // clicks inside never reach the overlay behind
    MouseArea {
        anchors.fill: parent
        acceptedButtons: Qt.AllButtons
    }

    component RoundButton: Rectangle {
        id: button
        property string iconName
        property string label
        signal clicked()
        implicitWidth: label ? buttonText.implicitWidth + 20 : 28
        implicitHeight: 28
        radius: 14
        color: buttonHover.hovered ? Qt.rgba(cal.fg.r, cal.fg.g, cal.fg.b, 0.12) : "transparent"
        Kirigami.Icon {
            visible: !button.label
            anchors.centerIn: parent
            width: 16
            height: 16
            source: button.iconName
        }
        Text {
            id: buttonText
            visible: !!button.label
            anchors.centerIn: parent
            text: button.label
            color: Kirigami.Theme.highlightColor
            font.pointSize: Kirigami.Theme.defaultFont.pointSize
        }
        HoverHandler {
            id: buttonHover
        }
        TapHandler {
            onTapped: button.clicked()
        }
    }

    ColumnLayout {
        id: column
        x: 14
        y: 14
        width: parent.width - 28
        spacing: 6

        RowLayout {
            Layout.fillWidth: true
            spacing: 2
            Text {
                Layout.fillWidth: true
                leftPadding: 6
                text: cal.locale.standaloneMonthName(cal.month, Locale.LongFormat) + " " + cal.year
                font.bold: true
                font.pointSize: Kirigami.Theme.defaultFont.pointSize * 1.1
                color: cal.fg
            }
            RoundButton {
                label: qsTr("Today")
                visible: cal.month !== cal.today.getMonth() || cal.year !== cal.today.getFullYear()
                onClicked: cal.reset()
            }
            RoundButton {
                iconName: "go-previous"
                onClicked: cal.step(-1)
            }
            RoundButton {
                iconName: "go-next"
                onClicked: cal.step(1)
            }
        }

        Grid {
            columns: 7
            Repeater {
                model: 7
                Text {
                    required property int index
                    width: cal.cell
                    horizontalAlignment: Text.AlignHCenter
                    text: cal.locale.dayName((cal.locale.firstDayOfWeek + index) % 7, Locale.NarrowFormat)
                    color: Kirigami.Theme.disabledTextColor
                    font.pointSize: Kirigami.Theme.smallFont.pointSize
                }
            }
        }

        Grid {
            columns: 7
            Repeater {
                model: 42
                Item {
                    id: day
                    required property int index
                    readonly property var date: {
                        const first = new Date(cal.year, cal.month, 1);
                        const offset = (first.getDay() - cal.locale.firstDayOfWeek + 7) % 7;
                        return new Date(cal.year, cal.month, 1 - offset + index);
                    }
                    readonly property bool inMonth: date.getMonth() === cal.month
                    readonly property bool isToday: date.toDateString() === cal.today.toDateString()
                    width: cal.cell
                    height: cal.cell * 0.88

                    Rectangle {
                        anchors.centerIn: parent
                        width: Math.min(parent.width, parent.height) - 2
                        height: width
                        radius: width / 2
                        visible: day.isToday
                        color: Kirigami.Theme.highlightColor
                    }
                    Text {
                        anchors.centerIn: parent
                        text: day.date.getDate()
                        font.bold: day.isToday
                        font.pointSize: Kirigami.Theme.defaultFont.pointSize
                        color: day.isToday ? Kirigami.Theme.highlightedTextColor
                            : day.inMonth ? cal.fg : Kirigami.Theme.disabledTextColor
                    }
                }
            }
        }
    }
}
