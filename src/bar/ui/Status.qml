/*
    What the bar shows about the machine, from Plasma's own modules: the
    network, Bluetooth, sound, screen and keyboard brightness, and power. Each
    loads on its own, so a missing module leaves just its glyph, slider and
    toggles out.
    SPDX-License-Identifier: GPL-3.0-or-later
*/
import QtQuick

QtObject {
    id: status

    function load(file) {
        const component = Qt.createComponent(file);
        if (component.status !== Component.Ready) {
            console.warn("bar:", file, "is unavailable:", component.errorString());
            return null;
        }
        return component.createObject(status);
    }

    readonly property var net: load("status/Network.qml")
    readonly property var bt: load("status/Bluetooth.qml")
    readonly property var sound: load("status/Sound.qml")
    readonly property var brightness: load("status/Brightness.qml")
    readonly property var keyboard: load("status/Keyboard.qml")
    readonly property var power: load("status/Power.qml")
}
