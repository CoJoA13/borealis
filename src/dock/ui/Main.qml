/*
    Borealis Dock: one surface per screen it lives on, and the overlay its
    menus open in.
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
}
