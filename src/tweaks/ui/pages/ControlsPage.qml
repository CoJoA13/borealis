/*
    Borealis Tweaks, the Control Center page: which toggles the bar's Control
    Center shows and in what order, its sliders, and what its button in the
    bar shows. Changes reach the running bar as you make them.
    SPDX-License-Identifier: GPL-3.0-or-later
*/
import QtQuick
import QtQuick.Controls as QQC2
import QtQuick.Layouts
import org.kde.kirigami as Kirigami
import "../controls"

Kirigami.ScrollablePage {
    id: page
    title: qsTr("Control Center")

    readonly property var pillNames: ({
        wifi: qsTr("Wi-Fi"), bluetooth: qsTr("Bluetooth"), night: qsTr("Night Light"), power: qsTr("Power Mode"),
        dark: qsTr("Dark Style"), dnd: qsTr("Do Not Disturb"), aurora: qsTr("Aurora"), awake: qsTr("Stay Awake"),
        airplane: qsTr("Airplane Mode"), hotspot: qsTr("Hotspot"), mic: qsTr("Microphone"),
        keyboard: qsTr("Keyboard Light"), screenshot: qsTr("Screenshot"), record: qsTr("Record Screen")
    })
    readonly property var pillIcons: ({
        wifi: "network-wireless", bluetooth: "network-bluetooth", night: "redshift-status-on",
        power: "speedometer", dark: "weather-clear-night", dnd: "notifications-disabled",
        aurora: "preferences-desktop-wallpaper", awake: "system-suspend-inhibited", airplane: "network-flightmode-on",
        hotspot: "network-wireless-hotspot", mic: "audio-input-microphone", keyboard: "input-keyboard-brightness",
        screenshot: "camera-photo", record: "media-record"
    })
    readonly property var pillHints: ({
        wifi: qsTr("On or off; its arrow lists networks"), bluetooth: qsTr("On or off; its arrow lists devices"),
        night: qsTr("Warmer colours after dark"), power: qsTr("Power Saver, Balanced or Performance"),
        dark: qsTr("Borealis Dark or Light"), dnd: qsTr("No banners; its arrow sets for how long"),
        aurora: qsTr("The wallpaper animated or still"), awake: qsTr("No sleeping or locking by itself"),
        airplane: qsTr("Wi-Fi and Bluetooth off together"), hotspot: qsTr("Share this computer's connection"),
        mic: qsTr("Mute or unmute the microphone"), keyboard: qsTr("Step through the keyboard's light"),
        screenshot: qsTr("A region, a window or the screen"), record: qsTr("Record a region, a window or the screen")
    })
    readonly property var sliderNames: ({
        brightness: qsTr("Screen brightness"), volume: qsTr("Volume"), microphone: qsTr("Microphone level"),
        keyboard: qsTr("Keyboard light")
    })
    readonly property var glyphNames: ({
        network: qsTr("Network"), bluetooth: qsTr("Bluetooth, while it's on"), sound: qsTr("Volume"),
        battery: qsTr("Battery")
    })
    readonly property var shown: barSettings.values.pills || []
    readonly property var hidden: barSettings.pills.filter(name => shown.indexOf(name) < 0)
    readonly property color ink: Kirigami.Theme.textColor

    component BarToggle: Toggle {
        target: barSettings
    }

    ColumnLayout {
        spacing: Kirigami.Units.largeSpacing

        Kirigami.InlineMessage {
            Layout.fillWidth: true
            visible: !barSettings.installed
            type: Kirigami.MessageType.Information
            text: qsTr("The Control Center is part of the Borealis Bar, which isn't on. What you set here waits for it.")
            actions: [
                Kirigami.Action {
                    text: qsTr("Switch to the bar")
                    icon.name: "dialog-ok-apply"
                    enabled: barSettings.canSwitch && !backend.busy
                    onTriggered: barSettings.enable()
                }
            ]
        }

        Kirigami.Heading {
            level: 3
            text: qsTr("Toggles")
        }
        QQC2.Label {
            Layout.fillWidth: true
            wrapMode: Text.WordWrap
            opacity: 0.8
            text: qsTr("The round buttons, two to a row, in this order. In the Control Center itself, the pencil button lets you drag them around.")
        }

        GridLayout {
            Layout.fillWidth: true
            columns: page.width > Kirigami.Units.gridUnit * 36 ? 2 : 1
            columnSpacing: Kirigami.Units.smallSpacing
            rowSpacing: Kirigami.Units.smallSpacing

            Repeater {
                model: page.shown
                delegate: Rectangle {
                    id: tile
                    required property string modelData
                    required property int index
                    Layout.fillWidth: true
                    Layout.preferredWidth: Kirigami.Units.gridUnit * 12
                    implicitHeight: tileRow.implicitHeight + Kirigami.Units.smallSpacing * 2
                    radius: height / 2
                    color: Qt.rgba(page.ink.r, page.ink.g, page.ink.b, 0.06)
                    border.width: 1
                    border.color: Qt.rgba(page.ink.r, page.ink.g, page.ink.b, 0.12)

                    RowLayout {
                        id: tileRow
                        anchors.fill: parent
                        anchors.leftMargin: Kirigami.Units.largeSpacing * 1.5
                        anchors.rightMargin: Kirigami.Units.smallSpacing
                        spacing: Kirigami.Units.smallSpacing
                        Kirigami.Icon {
                            source: page.pillIcons[tile.modelData]
                            Layout.preferredWidth: Kirigami.Units.iconSizes.smallMedium
                            Layout.preferredHeight: Kirigami.Units.iconSizes.smallMedium
                        }
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 0
                            QQC2.Label {
                                Layout.fillWidth: true
                                text: page.pillNames[tile.modelData]
                                elide: Text.ElideRight
                                font.weight: Font.DemiBold
                            }
                            QQC2.Label {
                                Layout.fillWidth: true
                                text: page.pillHints[tile.modelData]
                                elide: Text.ElideRight
                                font: Kirigami.Theme.smallFont
                                opacity: 0.7
                            }
                        }
                        QQC2.ToolButton {
                            icon.name: "go-up"
                            display: QQC2.AbstractButton.IconOnly
                            text: qsTr("Earlier")
                            enabled: tile.index > 0
                            QQC2.ToolTip.text: text
                            QQC2.ToolTip.visible: hovered
                            onClicked: barSettings.movePill(tile.modelData, -1)
                        }
                        QQC2.ToolButton {
                            icon.name: "go-down"
                            display: QQC2.AbstractButton.IconOnly
                            text: qsTr("Later")
                            enabled: tile.index < page.shown.length - 1
                            QQC2.ToolTip.text: text
                            QQC2.ToolTip.visible: hovered
                            onClicked: barSettings.movePill(tile.modelData, 1)
                        }
                        QQC2.ToolButton {
                            icon.name: "list-remove"
                            display: QQC2.AbstractButton.IconOnly
                            text: qsTr("Take it out")
                            QQC2.ToolTip.text: text
                            QQC2.ToolTip.visible: hovered
                            onClicked: barSettings.setPill(tile.modelData, false)
                        }
                    }
                }
            }
        }
        QQC2.Label {
            Layout.fillWidth: true
            visible: page.shown.length === 0
            wrapMode: Text.WordWrap
            opacity: 0.7
            text: qsTr("No toggles: the Control Center shows its sliders and what's playing.")
        }

        Kirigami.Heading {
            level: 3
            visible: page.hidden.length > 0
            text: qsTr("More toggles")
        }
        Flow {
            Layout.fillWidth: true
            spacing: Kirigami.Units.smallSpacing
            Repeater {
                model: page.hidden
                delegate: QQC2.Button {
                    required property string modelData
                    text: page.pillNames[modelData]
                    icon.name: page.pillIcons[modelData]
                    QQC2.ToolTip.text: page.pillHints[modelData]
                    QQC2.ToolTip.visible: hovered
                    QQC2.ToolTip.delay: Kirigami.Units.toolTipDelay
                    onClicked: barSettings.setPill(modelData, true)
                }
            }
        }
        QQC2.Label {
            Layout.fillWidth: true
            wrapMode: Text.WordWrap
            opacity: 0.7
            font: Kirigami.Theme.smallFont
            text: qsTr("A toggle this computer has no use for, like Keyboard Light without a lit keyboard, stays out of sight.")
        }

        Kirigami.FormLayout {
            Layout.fillWidth: true

            Kirigami.Separator {
                Kirigami.FormData.isSection: true
                Kirigami.FormData.label: qsTr("Sliders")
            }
            Repeater {
                model: barSettings.sliders
                delegate: QQC2.Switch {
                    required property string modelData
                    required property int index
                    readonly property bool chosen: (barSettings.values.sliders || []).indexOf(modelData) >= 0
                    Kirigami.FormData.label: index === 0 ? qsTr("Show:") : ""
                    text: page.sliderNames[modelData]
                    checked: chosen
                    onToggled: {
                        barSettings.setSlider(modelData, checked);
                        checked = Qt.binding(() => chosen);
                    }
                }
            }
            BarToggle {
                Kirigami.FormData.label: qsTr("What's playing:")
                key: "media"
            }

            Kirigami.Separator {
                Kirigami.FormData.isSection: true
                Kirigami.FormData.label: qsTr("Its button in the bar")
            }
            Repeater {
                model: barSettings.glyphs
                delegate: QQC2.Switch {
                    required property string modelData
                    required property int index
                    readonly property bool chosen: (barSettings.values.glyphs || []).indexOf(modelData) >= 0
                    Kirigami.FormData.label: index === 0 ? qsTr("Icons:") : ""
                    text: page.glyphNames[modelData]
                    checked: chosen
                    onToggled: {
                        barSettings.setGlyph(modelData, checked);
                        checked = Qt.binding(() => chosen);
                    }
                }
            }
            BarToggle {
                Kirigami.FormData.label: qsTr("Battery percentage:")
                key: "batteryPercent"
            }
        }

        Kirigami.Separator {
            Layout.fillWidth: true
        }

        Flow {
            Layout.fillWidth: true
            spacing: Kirigami.Units.smallSpacing
            QQC2.Button {
                text: qsTr("Open the Control Center")
                icon.name: "adjustlevels"
                enabled: barSettings.running
                onClicked: barSettings.openControlCenter("")
            }
            QQC2.Button {
                text: qsTr("Arrange it there")
                icon.name: "document-edit"
                enabled: barSettings.running
                onClicked: barSettings.openControlCenter("edit")
            }
            QQC2.Button {
                text: qsTr("Reset the Control Center")
                icon.name: "edit-undo"
                onClicked: barSettings.resetControls()
            }
        }

        JobLog {}
    }
}
