/*
    A month at a glance, for the clock's panel. Arrow keys or the buttons
    change the month.
    SPDX-License-Identifier: GPL-3.0-or-later
*/
import QtQuick
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

Item {
    id: cal

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

    implicitWidth: 7 * cell
    implicitHeight: column.implicitHeight
    Component.onCompleted: reset()

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
        width: parent.width
        spacing: 6

        Text {
            Layout.fillWidth: true
            leftPadding: 6
            text: cal.today.toLocaleDateString(cal.locale, "dddd")
            color: Kirigami.Theme.highlightColor
            font.pointSize: Kirigami.Theme.defaultFont.pointSize
        }
        Text {
            Layout.fillWidth: true
            leftPadding: 6
            text: cal.today.toLocaleDateString(cal.locale, "d MMMM yyyy")
            font.bold: true
            font.pointSize: Kirigami.Theme.defaultFont.pointSize * 1.3
            color: cal.fg
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.topMargin: 6
            spacing: 2
            Text {
                Layout.fillWidth: true
                leftPadding: 6
                text: cal.locale.standaloneMonthName(cal.month, Locale.LongFormat) + " " + cal.year
                font.bold: true
                font.pointSize: Kirigami.Theme.defaultFont.pointSize
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
