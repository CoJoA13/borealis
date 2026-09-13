/*
    The keyboard's backlight, from Plasma's brightness module.
    SPDX-License-Identifier: GPL-3.0-or-later
*/
import QtQuick
import org.kde.plasma.private.brightnesscontrolplugin

QtObject {
    id: keyboard

    property var control: KeyboardBrightnessControl {}

    readonly property int maximum: control.brightnessMax
    readonly property int level: control.brightness
    readonly property bool available: !!control.isBrightnessAvailable && maximum > 0
    readonly property real fraction: maximum > 0 ? level / maximum : 0
    readonly property string label: level <= 0 ? qsTr("Off")
        : maximum === 2 ? [qsTr("Low"), qsTr("High")][level - 1]
        : maximum === 3 ? [qsTr("Low"), qsTr("Medium"), qsTr("High")][level - 1]
        : qsTr("%1%").arg(Math.round(fraction * 100))

    function setLevel(value) {
        if (available) {
            control.brightness = Math.max(0, Math.min(maximum, Math.round(value)));
        }
    }
    function setFraction(fraction) {
        setLevel(fraction * maximum);
    }
    // brighter step by step, then off, the way a keyboard's own key goes
    function cycle() {
        setLevel(level >= maximum ? 0 : level + Math.max(1, Math.round(maximum / 3)));
    }
}
