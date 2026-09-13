/*
    Borealis Tweaks, the Presets page: the whole desktop in one go (the dock,
    the bar and its Control Center, the title bar and effects, hot corners
    and, in presets you save, the theme), with Undo, and files to share.
    SPDX-License-Identifier: GPL-3.0-or-later
*/
import QtQuick
import QtQuick.Controls as QQC2
import QtQuick.Layouts
import QtQuick.Dialogs as Dialogs
import org.kde.kirigami as Kirigami
import "../controls"

Kirigami.ScrollablePage {
    id: page
    title: qsTr("Presets")

    // the preset the Apply dialog is about, and whether its theme is ticked there
    property var picked: null
    property bool themeChosen: true
    readonly property var sectionNames: ({
        dock: qsTr("The dock's look"), dockApps: qsTr("The dock's apps, Stacks and widgets"), bar: qsTr("The bar"),
        controls: qsTr("The Control Center's toggles"), windows: qsTr("Title bar, window corners and effects"),
        desktop: qsTr("Hot corners, screen edges and clicks")
    })
    readonly property var variantNames: ({dark: qsTr("Dark"), light: qsTr("Light"), auto: qsTr("day and night")})

    function notify(message, ok) {
        applicationWindow().showPassiveNotification(message, ok === false ? 9000 : 4000);
    }
    function themeLine(preset) {
        const parts = [];
        if (preset.variant) {
            parts.push(page.variantNames[preset.variant]);
        }
        if (preset.paletteName) {
            parts.push(qsTr("%1 colours").arg(preset.paletteName));
        }
        if (preset.liveWallpaper === true || preset.liveWallpaper === false) {
            parts.push(preset.liveWallpaper ? qsTr("the animated aurora") : qsTr("a still wallpaper"));
        }
        return qsTr("Theme: %1").arg(parts.join(", "));
    }
    function pick(preset) {
        page.picked = preset;
        applyDialog.open();
    }
    function applyPicked() {
        const chosen = [];
        for (let i = 0; i < sectionBoxes.count; i++) {
            const box = sectionBoxes.itemAt(i);
            if (box && box.checked) {
                chosen.push(box.modelData);
            }
        }
        presetsSettings.apply(page.picked.id, chosen, remixBox.visible && page.themeChosen && remixBox.checked);
    }

    ColumnLayout {
        spacing: Kirigami.Units.largeSpacing

        Kirigami.InlineMessage {
            Layout.fillWidth: true
            visible: presetsSettings.canUndo && presetsSettings.lastApplied !== ""
            type: Kirigami.MessageType.Positive
            text: backend.busy ? qsTr("Putting %1 in place…").arg(presetsSettings.lastApplied)
                               : qsTr("%1 is on.").arg(presetsSettings.lastApplied)
            actions: [
                Kirigami.Action {
                    text: qsTr("Undo")
                    icon.name: "edit-undo"
                    enabled: !backend.busy
                    onTriggered: presetsSettings.undo()
                }
            ]
        }

        QQC2.Label {
            Layout.fillWidth: true
            wrapMode: Text.WordWrap
            text: qsTr("A whole desktop in one go: the dock, the bar and its Control Center, the title bar, window corners and effects, and the hot corners. Presets you save keep the theme as well. Your apps, fonts, touchpad and shortcuts stay as they are.")
        }

        Flow {
            Layout.fillWidth: true
            spacing: Kirigami.Units.largeSpacing

            Repeater {
                model: presetsSettings.presets
                delegate: PresetCard {
                    required property var modelData
                    width: Kirigami.Units.gridUnit * 12
                    text: modelData.name
                    subtitle: modelData.current ? qsTr("In use")
                        : modelData.description !== "" ? modelData.description
                        : modelData.builtin ? qsTr("Built in") : qsTr("Yours")
                    summary: modelData.thumb
                    selected: modelData.current
                    removable: !modelData.builtin
                    enabled: !backend.busy
                    onClicked: page.pick(modelData)
                    onRemoveRequested: presetsSettings.deletePreset(modelData.id)
                }
            }
        }

        Flow {
            Layout.fillWidth: true
            spacing: Kirigami.Units.smallSpacing
            QQC2.CheckBox {
                id: includeApps
                text: qsTr("With the dock's apps")
                QQC2.ToolTip.text: qsTr("Saving and exporting include the dock's apps, Stacks and widgets")
                QQC2.ToolTip.visible: hovered
            }
            QQC2.Button {
                text: qsTr("Save This Desktop…")
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

        Hint {
            text: qsTr("Saved and imported presets are files in %1. Undo remembers the desktop from before the last preset.")
                      .arg(presetsSettings.folder)
        }

        JobLog {}
    }

    Kirigami.Dialog {
        id: applyDialog
        title: page.picked ? qsTr("Apply %1").arg(page.picked.name) : ""
        preferredWidth: Kirigami.Units.gridUnit * 24
        padding: Kirigami.Units.largeSpacing
        standardButtons: QQC2.Dialog.Cancel
        customFooterActions: [
            Kirigami.Action {
                text: qsTr("Apply")
                icon.name: "dialog-ok-apply"
                enabled: !backend.busy
                onTriggered: {
                    page.applyPicked();
                    applyDialog.close();
                }
            }
        ]
        onOpened: {
            for (let i = 0; i < sectionBoxes.count; i++) {
                sectionBoxes.itemAt(i).checked = true;
            }
            remixBox.checked = true;
            page.themeChosen = true;
        }

        ColumnLayout {
            spacing: Kirigami.Units.smallSpacing

            QQC2.Label {
                Layout.fillWidth: true
                visible: text !== ""
                wrapMode: Text.WordWrap
                text: page.picked ? page.picked.description : ""
            }
            QQC2.Label {
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
                opacity: 0.8
                text: qsTr("It changes:")
            }
            Repeater {
                id: sectionBoxes
                model: page.picked ? page.picked.sections : []
                delegate: QQC2.CheckBox {
                    required property string modelData
                    Layout.fillWidth: true
                    checked: true
                    text: modelData === "theme" ? page.themeLine(page.picked) : page.sectionNames[modelData]
                    onToggled: if (modelData === "theme") {
                        page.themeChosen = checked;
                    }
                }
            }
            QQC2.CheckBox {
                id: remixBox
                Layout.fillWidth: true
                visible: page.picked !== null && page.picked.remix
                enabled: page.themeChosen
                text: qsTr("Rebuild the theme in its colours (about half a minute)")
            }
        }
    }

    Kirigami.PromptDialog {
        id: saveDialog
        title: qsTr("Save This Desktop")
        subtitle: includeApps.checked
            ? qsTr("The theme, the dock with its apps, the bar, the Control Center, the title bar and the hot corners, as they are now.")
            : qsTr("The theme, the dock's look, the bar, the Control Center, the title bar and the hot corners, as they are now.")
        standardButtons: QQC2.Dialog.Save | QQC2.Dialog.Cancel
        onOpened: {
            presetName.text = "";
            presetName.forceActiveFocus();
        }
        onAccepted: {
            if (presetsSettings.savePreset(presetName.text, includeApps.checked).length) {
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
        title: qsTr("Import a Desktop Preset")
        fileMode: Dialogs.FileDialog.OpenFile
        nameFilters: [qsTr("Desktop presets (*.json)"), qsTr("All files (*)")]
        onAccepted: {
            const result = presetsSettings.importPreset(selectedFile.toString());
            if (result.startsWith("error:")) {
                page.notify(qsTr("That file couldn't be imported: %1").arg(result.slice(6)), false);
            } else {
                page.notify(qsTr("Imported. Pick it to apply it."));
            }
        }
    }

    Dialogs.FileDialog {
        id: exportDialog
        title: qsTr("Export This Desktop")
        fileMode: Dialogs.FileDialog.SaveFile
        defaultSuffix: "json"
        nameFilters: [qsTr("Desktop presets (*.json)")]
        onAccepted: {
            const result = presetsSettings.exportPreset(selectedFile.toString(), includeApps.checked);
            if (result.startsWith("error:")) {
                page.notify(qsTr("Couldn't save it there: %1").arg(result.slice(6)), false);
            } else {
                page.notify(qsTr("Saved to %1").arg(result));
            }
        }
    }
}
