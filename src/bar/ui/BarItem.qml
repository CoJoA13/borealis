/*
    One of the bar's items, by name: menu, app, appmenu, clock, tray, drives,
    controls.
    SPDX-License-Identifier: GPL-3.0-or-later
*/
import QtQuick
import QtQuick.Layouts
import "items"

Loader {
    id: item

    property string name
    property var window
    property real limit: 1e9

    Layout.fillHeight: true
    // an item that has nothing to show (no drive plugged in, no menus) says so
    // with `wanted`; binding to its visibility instead would never let it show
    Layout.preferredWidth: item.item && item.item.wanted !== false ? item.item.implicitWidth : 0
    sourceComponent: ({
        menu: logo, app: appName, appmenu: titles, clock: clock, tray: tray, drives: drives, controls: controls
    })[item.name] || null

    Component {
        id: logo
        LogoButton {
            window: item.window
        }
    }
    Component {
        id: appName
        AppName {
            window: item.window
        }
    }
    Component {
        id: titles
        AppMenuTitles {
            window: item.window
            limit: item.limit - item.x
        }
    }
    Component {
        id: clock
        ClockItem {
            window: item.window
        }
    }
    Component {
        id: tray
        TrayItems {
            window: item.window
        }
    }
    Component {
        id: drives
        DrivesItem {
            window: item.window
        }
    }
    Component {
        id: controls
        ControlsItem {
            window: item.window
        }
    }
}
