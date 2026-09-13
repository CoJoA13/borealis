/*
    A slider with its value always in view.
    `target` is any settings object with a `values` map and a `set(key, value)`
    slot: the dock's, the bar's, or Plasma's.
    SPDX-License-Identifier: GPL-3.0-or-later
*/
import QtQuick
import QtQuick.Controls as QQC2
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

RowLayout {
    id: amount

    required property var target
    required property string key
    property real from: 0
    property real to: 100
    property real stepSize: 1
    property var describe: value => String(Math.round(value))

    spacing: Kirigami.Units.largeSpacing
    // a size the form can always fit, so the value never ends up off the page
    implicitWidth: Kirigami.Units.gridUnit * 18
    Layout.maximumWidth: Kirigami.Units.gridUnit * 24

    QQC2.Slider {
        id: slider
        Layout.fillWidth: true
        from: amount.from
        to: amount.to
        stepSize: amount.stepSize
        value: Number(amount.target.values[amount.key])
        onMoved: amount.target.set(amount.key, value)
        onPressedChanged: if (!pressed) {
            value = Qt.binding(() => Number(amount.target.values[amount.key]));
        }
    }

    QQC2.Label {
        // wide enough for the longest value, so the slider doesn't twitch
        Layout.minimumWidth: Math.max(implicitWidth, Kirigami.Units.gridUnit * 3.5)
        horizontalAlignment: Text.AlignRight
        font.features: { "tnum": 1 }
        text: amount.describe(slider.value)
    }
}
