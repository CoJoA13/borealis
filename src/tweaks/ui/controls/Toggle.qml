/*
    An on/off setting.
    SPDX-License-Identifier: GPL-3.0-or-later
*/
import QtQuick
import QtQuick.Controls as QQC2

QQC2.Switch {
    id: toggle

    required property var target
    required property string key

    checked: target.values[key] === true
    onToggled: {
        toggle.target.set(toggle.key, checked);
        // clicking replaces the binding; put it back
        checked = Qt.binding(() => toggle.target.values[toggle.key] === true);
    }
}
