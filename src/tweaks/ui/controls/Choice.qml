/*
    One of a few choices: `choices` is [[value, label], …].
    SPDX-License-Identifier: GPL-3.0-or-later
*/
import QtQuick
import QtQuick.Controls as QQC2

QQC2.ComboBox {
    id: combo

    required property var target
    required property string key
    property var choices: []

    function indexOfValue(value) {
        return Math.max(0, combo.choices.findIndex(c => c[0] === value));
    }

    model: choices.map(c => c[1])
    implicitContentWidthPolicy: QQC2.ComboBox.WidestText
    currentIndex: indexOfValue(target.values[key])
    onActivated: index => {
        combo.target.set(combo.key, combo.choices[index][0]);
        // picking replaces the binding; put it back
        currentIndex = Qt.binding(() => combo.indexOfValue(combo.target.values[combo.key]));
    }
}
