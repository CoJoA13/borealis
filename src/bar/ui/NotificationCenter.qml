/*
    The bar is the desktop's notification server: this holds Plasma's own
    notification models, one for the banners and one for the history under
    the clock, plus Do Not Disturb.
    SPDX-License-Identifier: GPL-3.0-or-later
*/
import QtQuick
import org.kde.notificationmanager as NotificationManager

QtObject {
    id: center

    property var settings: NotificationManager.Settings {}

    // Do Not Disturb, told to the server so notifications arriving meanwhile
    // are marked and never pop up afterwards
    property var inhibit: Binding {
        target: NotificationManager.Server
        property: "inhibited"
        value: center.doNotDisturb
    }

    // new notifications, until they time out or are dismissed
    property var popups: NotificationManager.Notifications {
        showNotifications: !center.doNotDisturb
        showAddedDuringInhibition: false
        showJobs: center.settings.jobsInNotifications && !center.doNotDisturb
        showExpired: false
        showDismissed: false
        expandUnread: true
        groupMode: NotificationManager.Notifications.GroupDisabled
        sortMode: NotificationManager.Notifications.SortByDate
        limit: 4
        urgencies: NotificationManager.Notifications.CriticalUrgency | NotificationManager.Notifications.NormalUrgency
                   | (center.settings.lowPriorityPopups ? NotificationManager.Notifications.LowUrgency : 0)
        blacklistedDesktopEntries: center.settings.popupBlacklistedApplications
        blacklistedNotifyRcNames: center.settings.popupBlacklistedServices
    }

    // everything since login, for the clock's panel
    property var history: NotificationManager.Notifications {
        showNotifications: true
        showJobs: true
        showExpired: true
        showDismissed: true
        expandUnread: true
        groupMode: NotificationManager.Notifications.GroupApplicationsFlat
        groupLimit: 3
        sortMode: NotificationManager.Notifications.SortByDate
        blacklistedDesktopEntries: center.settings.historyBlacklistedApplications
        blacklistedNotifyRcNames: center.settings.historyBlacklistedServices
    }

    property date now: new Date()
    property var clock: Timer {
        interval: 15000
        running: true
        repeat: true
        onTriggered: center.now = new Date()
    }

    readonly property bool doNotDisturb: {
        const until = center.settings.notificationsInhibitedUntil;
        return (!isNaN(until) && until > center.now) || center.settings.notificationsInhibitedByApplication;
    }
    readonly property int unread: history.unreadNotificationsCount
    readonly property int jobType: NotificationManager.Notifications.JobType
    readonly property int criticalUrgency: NotificationManager.Notifications.CriticalUrgency

    function setDoNotDisturb(minutes) {
        if (minutes > 0) {
            settings.notificationsInhibitedUntil = new Date(Date.now() + minutes * 60000);
        } else {
            settings.notificationsInhibitedUntil = new Date(NaN);
            settings.revokeApplicationInhibitions();
        }
        settings.save();
        now = new Date();
    }
    function markRead() {
        history.lastRead = new Date();
    }
    function clearHistory() {
        history.clear(NotificationManager.Notifications.ClearExpired);
    }
    function close(model, row) {
        model.close(model.index(row, 0));
    }
    function activate(model, row) {
        model.invokeDefaultAction(model.index(row, 0), NotificationManager.Notifications.Close);
    }
    function action(model, row, name) {
        model.invokeAction(model.index(row, 0), name, NotificationManager.Notifications.Close);
    }
    function expire(row) {
        popups.expire(popups.index(row, 0));
    }
    function startTimeout(row) {
        popups.startTimeout(popups.index(row, 0));
    }
    function stopTimeout(row) {
        popups.stopTimeout(popups.index(row, 0));
    }
}
