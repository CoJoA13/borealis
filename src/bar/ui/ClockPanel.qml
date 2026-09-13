/*
    Under the clock: the notifications on one side, the calendar on the other,
    and Do Not Disturb.
    SPDX-License-Identifier: GPL-3.0-or-later
*/
import QtQuick
import QtQuick.Controls as QQC2
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

Card {
    id: panel

    property var notices: null
    signal dismissed()

    width: 720
    height: Math.max(calendar.implicitHeight, 380) + 32
    focus: true
    Keys.onEscapePressed: dismissed()
    Keys.onLeftPressed: calendar.step(-1)
    Keys.onRightPressed: calendar.step(1)
    onVisibleChanged: if (visible) {
        calendar.reset();
    }

    RowLayout {
        x: 16
        y: 16
        width: panel.width - 32
        height: panel.height - 32
        spacing: 16

        ColumnLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 8

            RowLayout {
                Layout.fillWidth: true
                Text {
                    Layout.fillWidth: true
                    text: qsTr("Notifications")
                    font.bold: true
                    font.pointSize: Kirigami.Theme.defaultFont.pointSize * 1.05
                    color: Kirigami.Theme.textColor
                }
                TextButton {
                    visible: !!panel.notices && list.count > 0
                    text: qsTr("Clear")
                    onClicked: panel.notices.clearHistory()
                }
            }

            ListView {
                id: list
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                spacing: 6
                model: panel.notices ? panel.notices.history : null
                delegate: NotificationRow {
                    width: ListView.view.width
                    notices: panel.notices
                    source: panel.notices ? panel.notices.history : null
                }
                Text {
                    anchors.centerIn: parent
                    visible: list.count === 0
                    text: panel.notices ? qsTr("No notifications") : qsTr("Notifications are unavailable")
                    color: Kirigami.Theme.disabledTextColor
                    font.pointSize: Kirigami.Theme.defaultFont.pointSize
                }
            }

            RowLayout {
                Layout.fillWidth: true
                visible: !!panel.notices
                spacing: 8
                Kirigami.Icon {
                    source: "notifications-disabled"
                    Layout.preferredWidth: 16
                    Layout.preferredHeight: 16
                }
                Text {
                    Layout.fillWidth: true
                    text: qsTr("Do Not Disturb")
                    color: Kirigami.Theme.textColor
                    font.pointSize: Kirigami.Theme.defaultFont.pointSize
                }
                Text {
                    visible: !!panel.notices && panel.notices.doNotDisturb
                             && !isNaN(panel.notices.settings.notificationsInhibitedUntil)
                    text: visible ? qsTr("until %1").arg(panel.notices.settings.notificationsInhibitedUntil
                                                           .toLocaleTimeString(Qt.locale(), Locale.ShortFormat)) : ""
                    color: Kirigami.Theme.disabledTextColor
                    font.pointSize: Kirigami.Theme.smallFont.pointSize
                }
                QQC2.Switch {
                    checked: !!panel.notices && panel.notices.doNotDisturb
                    onToggled: {
                        panel.notices.setDoNotDisturb(checked ? 60 : 0);
                        checked = Qt.binding(() => !!panel.notices && panel.notices.doNotDisturb);
                    }
                }
            }
        }

        Rectangle {
            Layout.fillHeight: true
            implicitWidth: 1
            color: Qt.rgba(panel.fg.r, panel.fg.g, panel.fg.b, 0.12)
        }

        Calendar {
            id: calendar
            Layout.alignment: Qt.AlignTop
        }
    }
}
