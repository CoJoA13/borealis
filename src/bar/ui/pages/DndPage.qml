/*
    The Control Center's Do Not Disturb page: on for a while, until a time of
    day, or until turned off.
    SPDX-License-Identifier: GPL-3.0-or-later
*/
import QtQuick
import QtQuick.Layouts
import org.kde.kirigami as Kirigami
import ".."

ColumnLayout {
    id: page

    required property var center
    readonly property var notices: center.notices
    readonly property bool quiet: !!notices && notices.doNotDisturb
    property date now: new Date()

    function at(hours, days) {
        const date = new Date(page.now.getTime());
        date.setDate(date.getDate() + days);
        date.setHours(hours, 0, 0, 0);
        return date;
    }
    readonly property var choices: {
        const hour = page.now.getHours();
        const list = [
            {key: "hour", text: qsTr("For 1 hour"), until: new Date(page.now.getTime() + 3600000)},
            {key: "hours", text: qsTr("For 4 hours"), until: new Date(page.now.getTime() + 4 * 3600000)}
        ];
        if (hour < 18) {
            list.push({key: "evening", text: qsTr("Until this evening"), until: page.at(18, 0)});
        }
        list.push({key: "morning", text: hour < 7 ? qsTr("Until this morning") : qsTr("Until tomorrow morning"),
                   until: page.at(7, hour < 7 ? 0 : 1)});
        list.push({key: "off", text: qsTr("Until I turn it off"), until: null});
        return list;
    }
    function untilText() {
        if (!page.quiet) {
            return qsTr("Notifications pop up as they arrive.");
        }
        const until = page.notices.doNotDisturbUntil;
        if (isNaN(until) || until <= page.now) {
            return page.notices.doNotDisturbByApp ? qsTr("An app turned it on.") : qsTr("On.");
        }
        if (until.getTime() - page.now.getTime() > 180 * 86400000) {
            return qsTr("On until you turn it off.");
        }
        const time = Qt.formatTime(until, Qt.locale().timeFormat(Locale.ShortFormat));
        return until.toDateString() === page.now.toDateString() ? qsTr("On until %1.").arg(time)
            : qsTr("On until %1 %2.").arg(Qt.locale().dayName(until.getDay(), Locale.ShortFormat)).arg(time);
    }

    spacing: 4

    Timer {
        interval: 30000
        repeat: true
        running: page.visible
        onTriggered: page.now = new Date()
    }

    PageHeader {
        Layout.fillWidth: true
        title: qsTr("Do Not Disturb")
        switchVisible: !!page.notices
        checked: page.quiet
        onBack: page.center.back()
        onToggled: on => {
            if (on) {
                page.notices.setDoNotDisturbUntil(page.center.forever());
            } else {
                page.notices.setDoNotDisturb(0);
            }
        }
    }

    Text {
        Layout.fillWidth: true
        Layout.leftMargin: 10
        Layout.rightMargin: 10
        Layout.bottomMargin: 4
        text: page.notices ? page.untilText() : qsTr("Notifications aren't available.")
        wrapMode: Text.WordWrap
        font.pointSize: Kirigami.Theme.defaultFont.pointSize
        color: Kirigami.Theme.disabledTextColor
    }

    Repeater {
        model: page.notices ? page.choices : []
        delegate: ListRow {
            required property var modelData
            objectName: "dnd-" + modelData.key
            Layout.fillWidth: true
            title: modelData.text
            onClicked: page.notices.setDoNotDisturbUntil(modelData.until || page.center.forever())
        }
    }

    RowLayout {
        Layout.fillWidth: true
        Layout.topMargin: 4
        Item {
            Layout.fillWidth: true
        }
        TextButton {
            text: qsTr("Notification Settings…")
            onClicked: {
                page.center.dismissed();
                bar.openKcm("kcm_notifications");
            }
        }
    }
}
