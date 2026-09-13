/*
    The clock, with a dot for unread notifications (or the Do Not Disturb
    glyph). Clicking it opens the notifications and the calendar.
    SPDX-License-Identifier: GPL-3.0-or-later
*/
import QtQuick
import org.kde.kirigami as Kirigami
import ".."

BarButton {
    id: clock

    property var window
    property date now: new Date()
    readonly property var notices: window ? window.notices : null
    readonly property var cfg: bar.settings.values
    readonly property string shortTime: Qt.locale().timeFormat(Locale.ShortFormat)
    readonly property bool hours24: cfg.clockHours === "24"
        || (cfg.clockHours === "auto" && shortTime.indexOf("AP") < 0 && shortTime.indexOf("ap") < 0)
    readonly property string format: (cfg.clockWeekday ? "ddd " : "") + (cfg.clockDate ? "d MMM  " : "")
        + (hours24 ? "HH:mm" : "h:mm") + (cfg.clockSeconds ? ":ss" : "") + (hours24 ? "" : " AP")

    name: "clock"
    active: bar.popup === "clock"
    implicitWidth: row.implicitWidth + 20

    Timer {
        interval: 1000
        running: true
        repeat: true
        onTriggered: clock.now = new Date()
    }

    Row {
        id: row
        anchors.centerIn: parent
        spacing: 6
        Kirigami.Icon {
            anchors.verticalCenter: parent.verticalCenter
            visible: !!clock.notices && clock.notices.doNotDisturb
            source: "notifications-disabled"
            width: 14
            height: 14
        }
        Text {
            anchors.verticalCenter: parent.verticalCenter
            text: clock.now.toLocaleString(Qt.locale(), clock.format.trim())
            font.pointSize: Kirigami.Theme.defaultFont.pointSize
            font.features: { "tnum": 1 }
            color: Kirigami.Theme.textColor
        }
        Rectangle {
            anchors.verticalCenter: parent.verticalCenter
            visible: !!clock.notices && !clock.notices.doNotDisturb && clock.notices.unread > 0
            width: 6
            height: 6
            radius: 3
            color: Kirigami.Theme.highlightColor
        }
    }

    onClicked: {
        const r = clock.windowRect();
        bar.openPanel("clock", clock.window.targetScreen, r.x, r.y, r.width, r.height);
    }
}
