/*
    Borealis Dock: one surface per screen it lives on, the overlay its menus
    open in, and Launchpad.
    SPDX-License-Identifier: GPL-3.0-or-later
*/
import QtQuick
import QtQml

QtObject {
    id: root

    property var docks: Instantiator {
        model: dock.screens
        delegate: DockWindow {
            required property var modelData
            targetScreen: modelData
        }
    }

    property var overlay: Overlay {}

    property var launchpad: Launchpad {}
}
