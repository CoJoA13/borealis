/*
    True while a maximized or fullscreen window is on this screen (and the
    desktop isn't being peeked at).
    SPDX-License-Identifier: GPL-3.0-or-later
*/

import QtQuick
import QtQuick.Window
import org.kde.kwindowsystem
import org.kde.taskmanager as TaskManager

Item {
    id: detector

    property bool anyBlocking: false
    readonly property bool covered: anyBlocking && !KWindowSystem.showingDesktop

    TaskManager.ActivityInfo { id: activities }

    TaskManager.TasksModel {
        id: tasks
        groupMode: TaskManager.TasksModel.GroupDisabled
        // must equal the window's screen rectangle exactly
        screenGeometry: Qt.rect(detector.Screen.virtualX, detector.Screen.virtualY,
                                detector.Screen.width, detector.Screen.height)
        activity: activities.currentActivity
        filterByScreen: true
        filterByCurrentVirtualDesktop: true   // per screen in Plasma 6.7
        filterByActivity: true
        filterMinimized: true
        filterHidden: true
    }

    Repeater {
        id: windows
        model: tasks
        delegate: Item {
            readonly property bool blocks: model.IsMaximized === true || model.IsFullScreen === true
            onBlocksChanged: Qt.callLater(detector.update)
        }
        onItemAdded: Qt.callLater(detector.update)
        onItemRemoved: Qt.callLater(detector.update)
    }

    function update() {
        let any = false;
        for (let i = 0; i < windows.count; ++i) {
            const item = windows.itemAt(i);
            if (item && item.blocks) {
                any = true;
                break;
            }
        }
        anyBlocking = any;
    }
}
