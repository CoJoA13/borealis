/*
    Lock, sleep, restart, shut down and log out, through Plasma's own session
    management (which asks for confirmation the Plasma way).
    SPDX-License-Identifier: GPL-3.0-or-later
*/
import QtQuick
import org.kde.plasma.private.sessions as Sessions

QtObject {
    id: sessions

    property var manager: Sessions.SessionManagement {}

    function run(action) {
        switch (action) {
        case "lock":
            manager.lock();
            break;
        case "sleep":
            manager.suspend();
            break;
        case "restart":
            manager.requestReboot();
            break;
        case "shutdown":
            manager.requestShutdown();
            break;
        case "logout":
            manager.requestLogout();
            break;
        }
    }

    Component.onCompleted: bar.setSessionCapabilities({
        lock: manager.canLock, suspend: manager.canSuspend, reboot: manager.canReboot,
        shutdown: manager.canShutdown, logout: manager.canLogout
    })
}
