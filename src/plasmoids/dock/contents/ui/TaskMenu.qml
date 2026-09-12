/*
    The dock's right-click menu: everything goes through TasksModel.
    SPDX-License-Identifier: GPL-3.0-or-later
*/

import QtQuick
import org.kde.plasma.components as PlasmaComponents3

PlasmaComponents3.Menu {
    id: menu

    property int taskIndex: -1
    property bool isLauncher: false
    property bool hasWindow: false

    function popup(item) {
        menu.popup(item, 0, -menu.height);
    }

    PlasmaComponents3.MenuItem {
        text: i18nd("plasma_applet_org.borealis.dock", "Open new window")
        icon.name: "window-new"
        onTriggered: tasks.requestNewInstance(tasks.makeModelIndex(menu.taskIndex))
    }

    PlasmaComponents3.MenuItem {
        text: menu.isLauncher ? i18nd("plasma_applet_org.borealis.dock", "Unpin from dock")
                              : i18nd("plasma_applet_org.borealis.dock", "Pin to dock")
        icon.name: menu.isLauncher ? "window-unpin" : "window-pin"
        onTriggered: {
            const idx = tasks.makeModelIndex(menu.taskIndex);
            if (menu.isLauncher) {
                tasks.requestRemoveLauncher(idx);
            } else {
                tasks.requestAddLauncher(idx);
            }
        }
    }

    PlasmaComponents3.MenuItem {
        text: i18nd("plasma_applet_org.borealis.dock", "Close")
        icon.name: "window-close"
        enabled: menu.hasWindow
        onTriggered: tasks.requestClose(tasks.makeModelIndex(menu.taskIndex))
    }

    onClosed: menu.destroy()
}
