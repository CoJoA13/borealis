/*
    The built-in screen's brightness, from Plasma's brightness module.
    SPDX-License-Identifier: GPL-3.0-or-later
*/
import QtQuick
import org.kde.plasma.private.brightnesscontrolplugin

QtObject {
    id: screenLight

    property var control: ScreenBrightnessControl {}
    property string display: ""
    property int level: 0
    property int maximum: 0
    // the first display is the one the slider moves
    property var finder: Instantiator {
        model: screenLight.control.displays
        delegate: QtObject {
            required property int index
            required property string displayName
            required property int brightness
            required property int maxBrightness
            function push() {
                if (index === 0) {
                    screenLight.display = displayName;
                    screenLight.level = brightness;
                    screenLight.maximum = maxBrightness;
                }
            }
            onBrightnessChanged: push()
            onMaxBrightnessChanged: push()
            Component.onCompleted: push()
        }
    }

    readonly property bool available: maximum > 0
    readonly property real fraction: maximum > 0 ? level / maximum : 0

    function setFraction(fraction) {
        if (maximum > 0) {
            control.setBrightness(display, Math.round(Math.max(0.01, Math.min(1, fraction)) * maximum));
        }
    }
}
