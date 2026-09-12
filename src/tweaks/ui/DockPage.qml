/*
    Borealis Tweaks, the Dock page: everything about the standalone dock.
    Changes reach the running dock as you make them.
    SPDX-License-Identifier: GPL-3.0-or-later
*/
import QtQuick
import QtQuick.Controls as QQC2
import QtQuick.Layouts
import QtQuick.Dialogs as Dialogs
import org.kde.kirigami as Kirigami

Kirigami.ScrollablePage {
    id: page
    title: qsTr("Dock")

    // one of a few choices: [[value, label], …]
    component Choice: QQC2.ComboBox {
        id: combo
        required property string key
        property var choices: []
        model: choices.map(c => c[1])
        implicitContentWidthPolicy: QQC2.ComboBox.WidestText
        currentIndex: Math.max(0, choices.findIndex(c => c[0] === dockSettings.values[combo.key]))
        onActivated: index => {
            dockSettings.set(combo.key, combo.choices[index][0]);
            currentIndex = Qt.binding(() => Math.max(0, combo.choices.findIndex(c => c[0] === dockSettings.values[combo.key])));
        }
    }

    component Toggle: QQC2.Switch {
        id: toggle
        required property string key
        checked: dockSettings.values[toggle.key] === true
        onToggled: {
            dockSettings.set(toggle.key, checked);
            checked = Qt.binding(() => dockSettings.values[toggle.key] === true);
        }
    }

    component Amount: RowLayout {
        id: amount
        required property string key
        property real from: 0
        property real to: 100
        property real stepSize: 1
        property var describe: value => String(Math.round(value))
        QQC2.Slider {
            id: slider
            Layout.fillWidth: true
            Layout.minimumWidth: Kirigami.Units.gridUnit * 11
            from: amount.from
            to: amount.to
            stepSize: amount.stepSize
            value: dockSettings.values[amount.key]
            onMoved: dockSettings.set(amount.key, value)
            onPressedChanged: if (!pressed) {
                value = Qt.binding(() => dockSettings.values[amount.key]);
            }
        }
        QQC2.Label {
            Layout.minimumWidth: Kirigami.Units.gridUnit * 4
            text: amount.describe(slider.value)
        }
    }

    Connections {
        target: backend
        function onFinished(ok, message) {
            applicationWindow().showPassiveNotification(message, ok ? 6000 : 12000);
        }
    }

    ColumnLayout {
        spacing: Kirigami.Units.largeSpacing

        Kirigami.InlineMessage {
            Layout.fillWidth: true
            visible: !dockSettings.installed
            type: Kirigami.MessageType.Information
            text: qsTr("You're using the panel dock. The standalone Borealis Dock magnifies without a ceiling and has everything on this page.")
            actions: [
                Kirigami.Action {
                    text: qsTr("Switch to it")
                    icon.name: "dialog-ok-apply"
                    enabled: dockSettings.canSwitch && !backend.busy
                    onTriggered: dockSettings.enable()
                }
            ]
        }

        Kirigami.InlineMessage {
            Layout.fillWidth: true
            visible: dockSettings.installed && !dockSettings.running
            type: Kirigami.MessageType.Warning
            text: qsTr("The dock isn't running.")
            actions: [
                Kirigami.Action {
                    text: qsTr("Start it")
                    icon.name: "media-playback-start"
                    onTriggered: dockSettings.restart()
                }
            ]
        }

        Kirigami.FormLayout {
            Layout.fillWidth: true

            Kirigami.Separator {
                Kirigami.FormData.isSection: true
                Kirigami.FormData.label: qsTr("Place")
            }
            Choice {
                Kirigami.FormData.label: qsTr("Screen edge:")
                key: "position"
                choices: [["bottom", qsTr("Bottom")], ["left", qsTr("Left")], ["right", qsTr("Right")]]
            }
            Choice {
                Kirigami.FormData.label: qsTr("Show on:")
                key: "screen"
                choices: [["primary", qsTr("The primary screen")], ["all", qsTr("Every screen")],
                          ["follow", qsTr("The screen with the pointer")]]
            }
            Choice {
                Kirigami.FormData.label: qsTr("Hiding:")
                key: "hide"
                choices: [["always", qsTr("Always visible")], ["dodge", qsTr("Hide when a window covers it")],
                          ["auto", qsTr("Hide when not in use")]]
            }
            Amount {
                Kirigami.FormData.label: qsTr("Hide after:")
                visible: dockSettings.values.hide === "auto"
                key: "hideDelay"
                to: 2000
                stepSize: 50
                describe: value => qsTr("%1 ms").arg(Math.round(value))
            }

            Kirigami.Separator {
                Kirigami.FormData.isSection: true
                Kirigami.FormData.label: qsTr("Size")
            }
            Amount {
                Kirigami.FormData.label: qsTr("Icons:")
                key: "iconSize"
                from: 24
                to: 128
                stepSize: 2
                describe: value => qsTr("%1 px").arg(Math.round(value))
            }
            Amount {
                Kirigami.FormData.label: qsTr("Magnification:")
                key: "zoom"
                from: 1
                to: 3
                stepSize: 0.05
                describe: value => value <= 1.001 ? qsTr("Off") : qsTr("%1×").arg(value.toFixed(2))
            }
            Amount {
                Kirigami.FormData.label: qsTr("Spread:")
                key: "reach"
                from: 1
                to: 6
                stepSize: 0.25
                describe: value => qsTr("%1 icons").arg(value.toFixed(1))
            }
            Amount {
                Kirigami.FormData.label: qsTr("Spacing:")
                key: "spacing"
                to: 24
                describe: value => qsTr("%1 px").arg(Math.round(value))
            }
            Amount {
                Kirigami.FormData.label: qsTr("Gap to the edge:")
                key: "margin"
                to: 40
                describe: value => qsTr("%1 px").arg(Math.round(value))
            }

            Kirigami.Separator {
                Kirigami.FormData.isSection: true
                Kirigami.FormData.label: qsTr("Look")
            }
            Toggle {
                Kirigami.FormData.label: qsTr("Frosted glass:")
                key: "blur"
            }
            Amount {
                Kirigami.FormData.label: qsTr("Background:")
                key: "opacity"
                to: 1
                stepSize: 0.02
                describe: value => qsTr("%1%").arg(Math.round(value * 100))
            }
            Amount {
                Kirigami.FormData.label: qsTr("Corners:")
                key: "radius"
                to: 40
                describe: value => qsTr("%1 px").arg(Math.round(value))
            }
            Toggle {
                Kirigami.FormData.label: qsTr("Outline:")
                key: "border"
            }
            Choice {
                Kirigami.FormData.label: qsTr("Open apps:")
                key: "indicator"
                choices: [["dot", qsTr("A dot")], ["line", qsTr("A line")], ["none", qsTr("No mark")]]
            }
            Toggle {
                Kirigami.FormData.label: qsTr("Dividers:")
                key: "divider"
            }
            Toggle {
                Kirigami.FormData.label: qsTr("Names on hover:")
                key: "labels"
            }
            Toggle {
                Kirigami.FormData.label: qsTr("Badges and progress:")
                key: "badges"
            }
            Toggle {
                Kirigami.FormData.label: qsTr("Trash:")
                key: "showTrash"
            }

            Kirigami.Separator {
                Kirigami.FormData.isSection: true
                Kirigami.FormData.label: qsTr("Behaviour")
            }
            Choice {
                Kirigami.FormData.label: qsTr("Clicking the front app:")
                key: "clickAction"
                choices: [["expose", qsTr("Shows its windows")], ["cycle", qsTr("Steps through its windows")],
                          ["minimize", qsTr("Minimises it")]]
            }
            Toggle {
                Kirigami.FormData.label: qsTr("Bounce while opening:")
                key: "bounce"
            }
            Amount {
                Kirigami.FormData.label: qsTr("Animations:")
                key: "animation"
                to: 2
                stepSize: 0.25
                describe: value => value <= 0 ? qsTr("Off") : qsTr("%1×").arg(value.toFixed(2))
            }
            RowLayout {
                Kirigami.FormData.label: qsTr("Meta+1…9:")
                Toggle {
                    key: "shortcuts"
                }
                QQC2.Label {
                    visible: dockSettings.values.shortcuts === true && dockSettings.running
                    opacity: 0.7
                    text: dockSettings.shortcutKey.length ? qsTr("open the dock's first nine apps")
                                                          : qsTr("taken by another shortcut")
                }
                QQC2.Button {
                    visible: dockSettings.values.shortcuts === true && dockSettings.running
                             && dockSettings.shortcutKey.length === 0
                    text: qsTr("Shortcuts…")
                    icon.name: "preferences-desktop-keyboard-shortcut"
                    onClicked: dockSettings.openShortcuts()
                }
            }

            Kirigami.Separator {
                Kirigami.FormData.isSection: true
                Kirigami.FormData.label: qsTr("Stacks")
            }
            Repeater {
                model: dockSettings.values.stacks ? dockSettings.stackRows() : []
                delegate: RowLayout {
                    id: stackRow
                    required property var modelData
                    required property int index
                    readonly property var views: ["auto", "fan", "grid"]
                    readonly property var sorts: ["added", "modified", "name"]
                    readonly property var displays: ["stack", "folder"]
                    Kirigami.FormData.label: index === 0 ? qsTr("Folders:") : ""

                    Kirigami.Icon {
                        source: stackRow.modelData.icon
                        Layout.preferredWidth: Kirigami.Units.iconSizes.smallMedium
                        Layout.preferredHeight: Kirigami.Units.iconSizes.smallMedium
                    }
                    QQC2.Label {
                        Layout.minimumWidth: Kirigami.Units.gridUnit * 5
                        text: stackRow.modelData.name
                        QQC2.ToolTip.text: stackRow.modelData.real
                        QQC2.ToolTip.visible: nameHover.hovered
                        HoverHandler { id: nameHover }
                    }
                    QQC2.ComboBox {
                        model: [qsTr("Automatic"), qsTr("Fan"), qsTr("Grid")]
                        implicitContentWidthPolicy: QQC2.ComboBox.WidestText
                        currentIndex: stackRow.views.indexOf(stackRow.modelData.view)
                        onActivated: i => dockSettings.setStack(stackRow.index, "view", stackRow.views[i])
                    }
                    QQC2.ComboBox {
                        model: [qsTr("Date added"), qsTr("Date modified"), qsTr("Name")]
                        implicitContentWidthPolicy: QQC2.ComboBox.WidestText
                        currentIndex: stackRow.sorts.indexOf(stackRow.modelData.sort)
                        onActivated: i => dockSettings.setStack(stackRow.index, "sort", stackRow.sorts[i])
                    }
                    QQC2.ComboBox {
                        model: [qsTr("Stack"), qsTr("Folder")]
                        implicitContentWidthPolicy: QQC2.ComboBox.WidestText
                        currentIndex: stackRow.displays.indexOf(stackRow.modelData.display)
                        onActivated: i => dockSettings.setStack(stackRow.index, "display", stackRow.displays[i])
                    }
                    QQC2.ToolButton {
                        icon.name: "list-remove"
                        QQC2.ToolTip.text: qsTr("Remove from the dock")
                        QQC2.ToolTip.visible: hovered
                        onClicked: dockSettings.removeStack(stackRow.index)
                    }
                }
            }
            QQC2.Button {
                Kirigami.FormData.label: dockSettings.values.stacks && dockSettings.values.stacks.length ? "" : qsTr("Folders:")
                text: qsTr("Add a folder…")
                icon.name: "folder-new"
                onClicked: folderDialog.open()
            }

            Kirigami.Separator {
                Kirigami.FormData.isSection: true
                Kirigami.FormData.label: qsTr("Apps")
            }
            RowLayout {
                Kirigami.FormData.label: qsTr("Pinned:")
                QQC2.Label {
                    text: qsTr("%1 apps").arg(dockSettings.values.pinned ? dockSettings.values.pinned.length : 0)
                }
                QQC2.Button {
                    text: qsTr("Back to the Borealis set")
                    icon.name: "edit-reset"
                    onClicked: dockSettings.resetPins()
                }
            }
            QQC2.Label {
                Layout.fillWidth: true
                Layout.maximumWidth: Kirigami.Units.gridUnit * 26
                wrapMode: Text.WordWrap
                opacity: 0.7
                font: Kirigami.Theme.smallFont
                text: qsTr("Drag icons along the dock to reorder them, or off it to remove them. Drop an app from the launcher onto the dock to pin it, or a folder to make it a Stack.")
            }
        }

        Kirigami.Separator {
            Layout.fillWidth: true
        }

        RowLayout {
            Layout.fillWidth: true
            QQC2.Button {
                text: qsTr("Reset look and behaviour")
                icon.name: "edit-undo"
                onClicked: dockSettings.resetLook()
            }
            Item {
                Layout.fillWidth: true
            }
            QQC2.Button {
                visible: dockSettings.installed
                text: qsTr("Restart the dock")
                icon.name: "view-refresh"
                onClicked: dockSettings.restart()
            }
            QQC2.Button {
                visible: dockSettings.installed && dockSettings.canSwitch
                enabled: !backend.busy
                text: qsTr("Back to the panel dock")
                icon.name: "go-previous"
                onClicked: dockSettings.disable()
            }
        }

        QQC2.Label {
            Layout.fillWidth: true
            wrapMode: Text.WrapAnywhere
            opacity: 0.6
            font: Kirigami.Theme.smallFont
            text: qsTr("Settings file: %1").arg(dockSettings.configPath)
        }
    }

    Dialogs.FolderDialog {
        id: folderDialog
        title: qsTr("Choose a folder for the dock")
        onAccepted: dockSettings.addStack(selectedFolder.toString())
    }
}
