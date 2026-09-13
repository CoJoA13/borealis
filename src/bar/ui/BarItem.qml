/*
    One of the bar's items, by name: menu, app, appmenu, clock, tray, drives,
    controls.
    SPDX-License-Identifier: GPL-3.0-or-later
*/
import QtQuick
import QtQuick.Layouts
import "items"

// not "id: item": inside the components below that name would mean the
// Loader's own `item` property (the loaded button itself), and every button
// would lose its window
Loader {
    id: slot

    property string name
    property var window
    property real limit: 1e9

    Layout.fillHeight: true
    // an item that has nothing to show (no drive plugged in, no menus) says so
    // with `wanted`; binding to its visibility instead would never let it show
    Layout.preferredWidth: slot.item && slot.item.wanted !== false ? slot.item.implicitWidth : 0
    sourceComponent: ({
        menu: logo, app: appName, appmenu: titles, clock: clock, tray: tray, drives: drives, controls: controls
    })[slot.name] || null

    Component {
        id: logo
        LogoButton {
            window: slot.window
        }
    }
    Component {
        id: appName
        AppName {
            window: slot.window
        }
    }
    Component {
        id: titles
        AppMenuTitles {
            window: slot.window
            limit: slot.limit - slot.x
        }
    }
    Component {
        id: clock
        ClockItem {
            window: slot.window
        }
    }
    Component {
        id: tray
        TrayItems {
            window: slot.window
        }
    }
    Component {
        id: drives
        DrivesItem {
            window: slot.window
        }
    }
    Component {
        id: controls
        ControlsItem {
            window: slot.window
        }
    }
}
