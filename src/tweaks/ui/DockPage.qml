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

    function widgetOption(kind, key) {
        const w = (dockSettings.values.widgets || []).find(w => w.type === kind);
        return w ? w[key] : "";
    }
    function notify(message, ok) {
        applicationWindow().showPassiveNotification(message, ok === false ? 9000 : 4000);
    }

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

    // a widget in the dock, or not
    component WidgetSwitch: QQC2.Switch {
        id: widgetSwitch
        required property string kind
        checked: (dockSettings.values.widgets || []).some(w => w.type === widgetSwitch.kind)
        onToggled: {
            dockSettings.setWidget(widgetSwitch.kind, checked);
            checked = Qt.binding(() => (dockSettings.values.widgets || []).some(w => w.type === widgetSwitch.kind));
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

        // ---------------------------------------------------------- presets --
        Kirigami.Heading {
            level: 3
            text: qsTr("Presets")
        }

        Flow {
            Layout.fillWidth: true
            spacing: Kirigami.Units.smallSpacing

            Repeater {
                model: dockSettings.presets
                delegate: QQC2.AbstractButton {
                    id: card
                    required property var modelData
                    width: Kirigami.Units.gridUnit * 11
                    height: Kirigami.Units.gridUnit * 3.4
                    padding: Kirigami.Units.largeSpacing
                    hoverEnabled: true
                    onClicked: dockSettings.applyPreset(modelData.id, includeApps.checked && modelData.hasApps)
                    QQC2.ToolTip.visible: hovered && modelData.description.length > 0
                    QQC2.ToolTip.text: modelData.description

                    background: Rectangle {
                        radius: Kirigami.Units.cornerRadius
                        color: card.hovered
                            ? Qt.rgba(Kirigami.Theme.highlightColor.r, Kirigami.Theme.highlightColor.g,
                                      Kirigami.Theme.highlightColor.b, 0.14)
                            : Qt.rgba(Kirigami.Theme.textColor.r, Kirigami.Theme.textColor.g,
                                      Kirigami.Theme.textColor.b, 0.04)
                        border.width: card.modelData.current ? 2 : 1
                        border.color: card.modelData.current
                            ? Kirigami.Theme.highlightColor
                            : Qt.rgba(Kirigami.Theme.textColor.r, Kirigami.Theme.textColor.g,
                                      Kirigami.Theme.textColor.b, 0.2)
                    }
                    contentItem: RowLayout {
                        spacing: Kirigami.Units.smallSpacing
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 0
                            QQC2.Label {
                                Layout.fillWidth: true
                                text: card.modelData.name
                                font.bold: card.modelData.current
                                elide: Text.ElideRight
                            }
                            QQC2.Label {
                                Layout.fillWidth: true
                                text: card.modelData.current ? qsTr("In use")
                                    : card.modelData.builtin ? qsTr("Built in")
                                    : card.modelData.hasApps ? qsTr("Yours, with apps") : qsTr("Yours")
                                opacity: 0.7
                                font: Kirigami.Theme.smallFont
                                elide: Text.ElideRight
                            }
                        }
                        QQC2.ToolButton {
                            visible: !card.modelData.builtin
                            icon.name: "edit-delete"
                            QQC2.ToolTip.text: qsTr("Delete this preset")
                            QQC2.ToolTip.visible: hovered
                            onClicked: dockSettings.deletePreset(card.modelData.id)
                        }
                    }
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            QQC2.CheckBox {
                id: includeApps
                text: qsTr("With apps, Stacks and widgets")
                QQC2.ToolTip.text: qsTr("Saving and exporting include what's in your dock; picking a preset that has them brings them in")
                QQC2.ToolTip.visible: hovered
            }
            Item {
                Layout.fillWidth: true
            }
            QQC2.Button {
                text: qsTr("Save as Preset…")
                icon.name: "document-save"
                onClicked: saveDialog.open()
            }
            QQC2.Button {
                text: qsTr("Import…")
                icon.name: "document-import"
                onClicked: importDialog.open()
            }
            QQC2.Button {
                text: qsTr("Export…")
                icon.name: "document-export"
                onClicked: exportDialog.open()
            }
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
                Kirigami.FormData.label: qsTr("Window previews:")
                key: "previews"
            }
            Amount {
                Kirigami.FormData.label: qsTr("Previews after:")
                visible: dockSettings.values.previews === true
                key: "previewDelay"
                from: 100
                to: 1500
                stepSize: 50
                describe: value => qsTr("%1 ms").arg(Math.round(value))
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
                Kirigami.FormData.label: qsTr("Launchpad")
            }
            Toggle {
                Kirigami.FormData.label: qsTr("Icon in the dock:")
                key: "launchpad"
            }
            RowLayout {
                Kirigami.FormData.label: qsTr("Shortcut:")
                QQC2.Label {
                    text: dockSettings.launchpadKey.length ? dockSettings.launchpadKey
                        : dockSettings.running ? qsTr("None") : qsTr("Shown while the dock runs")
                }
                QQC2.Button {
                    text: qsTr("Change…")
                    icon.name: "preferences-desktop-keyboard-shortcut"
                    onClicked: dockSettings.openShortcuts()
                }
            }
            QQC2.Label {
                Layout.fillWidth: true
                Layout.maximumWidth: Kirigami.Units.gridUnit * 26
                wrapMode: Text.WordWrap
                opacity: 0.7
                font: Kirigami.Theme.smallFont
                text: qsTr("Meta on its own works too: give it to “Launchpad” under KWin in the shortcut settings, after taking it off the application launcher (or whatever holds it).")
            }

            Kirigami.Separator {
                Kirigami.FormData.isSection: true
                Kirigami.FormData.label: qsTr("Widgets")
            }
            RowLayout {
                Kirigami.FormData.label: qsTr("Clock:")
                WidgetSwitch {
                    kind: "clock"
                }
                QQC2.ComboBox {
                    id: clockStyle
                    visible: (dockSettings.values.widgets || []).some(w => w.type === "clock")
                    model: [qsTr("Analog"), qsTr("Digital")]
                    implicitContentWidthPolicy: QQC2.ComboBox.WidestText
                    currentIndex: page.widgetOption("clock", "style") === "digital" ? 1 : 0
                    onActivated: index => {
                        dockSettings.setWidgetOption("clock", "style", index === 1 ? "digital" : "analog");
                        currentIndex = Qt.binding(() => page.widgetOption("clock", "style") === "digital" ? 1 : 0);
                    }
                }
            }
            RowLayout {
                Kirigami.FormData.label: qsTr("Battery:")
                WidgetSwitch {
                    kind: "battery"
                }
                QQC2.Label {
                    opacity: 0.7
                    text: qsTr("shown when there is one")
                }
            }
            RowLayout {
                Kirigami.FormData.label: qsTr("Now playing:")
                WidgetSwitch {
                    kind: "media"
                }
                QQC2.Label {
                    opacity: 0.7
                    text: qsTr("shown while something plays")
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
                text: qsTr("Drag icons along the dock to reorder them, or off it to remove them. Drop an app from Launchpad or the launcher onto the dock to pin it, or a folder to make it a Stack.")
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

    Kirigami.PromptDialog {
        id: saveDialog
        title: qsTr("Save as Preset")
        subtitle: includeApps.checked ? qsTr("The current look, with your apps, Stacks and widgets.")
                                      : qsTr("The current look. Your apps stay out of it.")
        standardButtons: QQC2.Dialog.Save | QQC2.Dialog.Cancel
        onOpened: {
            presetName.text = "";
            presetName.forceActiveFocus();
        }
        onAccepted: {
            if (dockSettings.savePreset(presetName.text, includeApps.checked).length) {
                page.notify(qsTr("Saved “%1”").arg(presetName.text.trim()));
            }
        }
        QQC2.TextField {
            id: presetName
            placeholderText: qsTr("A name for it")
            onAccepted: saveDialog.accept()
        }
    }

    Dialogs.FileDialog {
        id: importDialog
        title: qsTr("Import a Dock Preset")
        fileMode: Dialogs.FileDialog.OpenFile
        nameFilters: [qsTr("Dock presets (*.json)"), qsTr("All files (*)")]
        onAccepted: {
            const result = dockSettings.importPreset(selectedFile.toString());
            if (result.startsWith("error:")) {
                page.notify(qsTr("That file couldn't be imported: %1").arg(result.slice(6)), false);
            } else {
                page.notify(qsTr("Imported. Pick it under Presets to use it."));
            }
        }
    }

    Dialogs.FileDialog {
        id: exportDialog
        title: qsTr("Export the Dock's Look")
        fileMode: Dialogs.FileDialog.SaveFile
        defaultSuffix: "json"
        nameFilters: [qsTr("Dock presets (*.json)")]
        onAccepted: {
            const result = dockSettings.exportPreset(selectedFile.toString(), includeApps.checked);
            if (result.startsWith("error:")) {
                page.notify(qsTr("Couldn't save it there: %1").arg(result.slice(6)), false);
            } else {
                page.notify(qsTr("Saved to %1").arg(result));
            }
        }
    }
}
