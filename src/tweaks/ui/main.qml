/*
    Borealis Tweaks — switch variant, remix the palette, control the
    animated wallpaper, and undo it all again.
    SPDX-License-Identifier: GPL-3.0-or-later
*/

import QtQuick
import QtQuick.Controls as QQC2
import QtQuick.Layouts
import QtQuick.Dialogs as Dialogs
import org.kde.kirigami as Kirigami

Kirigami.ApplicationWindow {
    id: root

    title: qsTr("Borealis Tweaks")
    minimumWidth: Kirigami.Units.gridUnit * 34
    minimumHeight: Kirigami.Units.gridUnit * 30
    width: minimumWidth
    height: Kirigami.Units.gridUnit * 42

    property string pendingAccent: backend.accent
    property string pendingName: backend.paletteName

    pageStack.initialPage: Kirigami.ScrollablePage {
        title: qsTr("Appearance")

        header: Kirigami.InlineMessage {
            visible: !backend.isBorealis
            position: Kirigami.InlineMessage.Header
            type: Kirigami.MessageType.Information
            text: qsTr("The current Global Theme is “%1”. Applying anything here switches to Borealis.")
                      .arg(backend.themeName)
        }

        ColumnLayout {
            spacing: Kirigami.Units.largeSpacing

            // ---------------------------------------------------- variant --
            Kirigami.FormLayout {
                Layout.fillWidth: true

                QQC2.ButtonGroup { id: variantGroup }

                RowLayout {
                    Kirigami.FormData.label: qsTr("Theme:")
                    Repeater {
                        model: [{k: "dark", t: qsTr("Dark")},
                                {k: "light", t: qsTr("Light")},
                                {k: "auto", t: qsTr("Day/night")}]
                        QQC2.RadioButton {
                            required property var modelData
                            text: modelData.t
                            enabled: !backend.busy
                            checked: backend.variant === modelData.k
                                QQC2.ButtonGroup.group: variantGroup
                            onToggled: {
                                if (checked && backend.variant !== modelData.k) {
                                    backend.setVariant(modelData.k);
                                }
                                // clicking replaces the binding; put it back
                                checked = Qt.binding(() => backend.variant === modelData.k);
                            }
                        }
                    }
                }

                QQC2.Switch {
                    id: liveSwitch
                    Kirigami.FormData.label: qsTr("Animated aurora:")
                    enabled: !backend.busy
                    checked: backend.liveWallpaper
                    text: checked ? qsTr("On, desktop and lock screen") : qsTr("Off")
                    onToggled: {
                        backend.setLiveWallpaper(checked);
                        // clicking a Switch replaces the binding; put it back
                        checked = Qt.binding(() => backend.liveWallpaper);
                    }
                }

                QQC2.Label {
                    Kirigami.FormData.label: qsTr("Palette:")
                    text: backend.paletteName + "  " + backend.accent
                }
            }

            Kirigami.Separator { Layout.fillWidth: true }

            // ----------------------------------------------------- remix ---
            Kirigami.Heading { level: 3; text: qsTr("Remix the palette") }
            QQC2.Label {
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
                opacity: 0.75
                text: backend.hasProject
                    ? qsTr("Pick a colour and the whole theme is rebuilt around it: windows, icons, cursors, wallpapers, the boot splash and the terminal. Takes about half a minute.")
                    : qsTr("The Borealis project folder was not found, so remixing is unavailable. Set BOREALIS_PROJECT to its path.")
            }

            Flow {
                Layout.fillWidth: true
                spacing: Kirigami.Units.smallSpacing

                Repeater {
                    model: backend.presets
                    delegate: QQC2.AbstractButton {
                        required property var modelData
                        width: Kirigami.Units.gridUnit * 7.5
                        height: Kirigami.Units.gridUnit * 3
                        enabled: backend.hasProject && !backend.busy
                        onClicked: {
                            root.pendingAccent = modelData.color;
                            root.pendingName = modelData.name === "Nocturne" ? "Borealis"
                                                                             : "Borealis " + modelData.name;
                        }
                        QQC2.ToolTip.visible: hovered
                        QQC2.ToolTip.text: modelData.hint
                        contentItem: RowLayout {
                            spacing: Kirigami.Units.smallSpacing
                            Rectangle {
                                Layout.preferredWidth: Kirigami.Units.gridUnit * 1.4
                                Layout.preferredHeight: Kirigami.Units.gridUnit * 1.4
                                radius: width / 2
                                color: modelData.color
                                border.width: root.pendingAccent === modelData.color ? 3 : 1
                                border.color: root.pendingAccent === modelData.color
                                              ? Kirigami.Theme.textColor
                                              : Qt.rgba(Kirigami.Theme.textColor.r, Kirigami.Theme.textColor.g,
                                                        Kirigami.Theme.textColor.b, 0.3)
                            }
                            QQC2.Label { text: modelData.name; elide: Text.ElideRight; Layout.fillWidth: true }
                        }
                    }
                }
            }

            RowLayout {
                Layout.fillWidth: true
                QQC2.Button {
                    text: qsTr("Custom colour…")
                    icon.name: "color-picker"
                    enabled: backend.hasProject && !backend.busy
                    onClicked: colorDialog.open()
                }
                QQC2.TextField {
                    Layout.fillWidth: true
                    placeholderText: qsTr("Name for this remix")
                    text: root.pendingName
                    enabled: backend.hasProject && !backend.busy
                    onTextEdited: root.pendingName = text
                }
            }

            RowLayout {
                Layout.fillWidth: true
                QQC2.CheckBox { id: gtkBox; text: qsTr("GTK apps"); checked: true; enabled: !backend.busy }
                QQC2.CheckBox { id: termBox; text: qsTr("Terminal"); checked: true; enabled: !backend.busy }
                Item { Layout.fillWidth: true }
                QQC2.Button {
                    text: backend.busy ? qsTr("Working…") : qsTr("Apply palette")
                    icon.name: "dialog-ok-apply"
                    enabled: backend.hasProject && !backend.busy && root.pendingName.length > 0
                    onClicked: backend.remix(root.pendingAccent, root.pendingName.trim(),
                                             gtkBox.checked, termBox.checked)
                }
            }

            QQC2.ProgressBar {
                Layout.fillWidth: true
                visible: backend.busy
                indeterminate: true
            }

            Kirigami.Separator { Layout.fillWidth: true }

            // ---------------------------------------------------- system ---
            Kirigami.Heading { level: 3; text: qsTr("Beyond Plasma") }

            Kirigami.FormLayout {
                Layout.fillWidth: true

                RowLayout {
                    Kirigami.FormData.label: qsTr("Flatpak apps:")
                    visible: backend.hasFlatpak
                    QQC2.Label {
                        text: backend.flatpakColors ? qsTr("Using the Borealis colours")
                                                    : qsTr("Still Adwaita grey")
                    }
                    QQC2.Button {
                        visible: !backend.flatpakColors
                        text: qsTr("Let them read the colours")
                        icon.name: "preferences-desktop-color"
                        onClicked: backend.grantFlatpakColors()
                    }
                }

                RowLayout {
                    Kirigami.FormData.label: qsTr("Boot splash:")
                    QQC2.Label {
                        text: backend.bootSplash.length ? backend.bootSplash : qsTr("unknown")
                    }
                    QQC2.Button {
                        visible: backend.hasProject && backend.bootSplash !== "borealis"
                        enabled: !backend.busy
                        text: qsTr("Install (asks for your password)")
                        icon.name: "system-reboot"
                        onClicked: backend.installSystemWide("--plymouth")
                    }
                }

                RowLayout {
                    Kirigami.FormData.label: qsTr("Login screen:")
                    QQC2.Label {
                        text: backend.systemWide ? qsTr("Theme is available to it")
                                                 : qsTr("Theme is only in your home folder")
                    }
                    QQC2.Button {
                        visible: backend.hasProject && !backend.systemWide
                        enabled: !backend.busy
                        text: qsTr("Copy system-wide")
                        icon.name: "system-upgrade"
                        onClicked: backend.installSystemWide("")
                    }
                    QQC2.Button {
                        text: qsTr("Open settings…")
                        icon.name: "preferences-system-login"
                        onClicked: backend.launch("login")
                    }
                }
            }

            QQC2.Label {
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
                opacity: 0.7
                font: Kirigami.Theme.smallFont
                text: qsTr("The login screen copies your look when you press “Apply Plasma Settings…” in its settings page; Plasma can't do that from here.")
            }

            Kirigami.Separator { Layout.fillWidth: true }

            // ------------------------------------------------------ undo ---
            RowLayout {
                Layout.fillWidth: true
                QQC2.ComboBox {
                    id: backupBox
                    Layout.fillWidth: true
                    model: backend.backups
                    displayText: count ? currentText : qsTr("No backups yet")
                    enabled: count > 0 && !backend.busy
                }
                QQC2.Button {
                    text: qsTr("Restore")
                    icon.name: "edit-undo"
                    enabled: backupBox.count > 0 && !backend.busy
                    onClicked: backend.restore(backupBox.currentText)
                }
            }

            RowLayout {
                Layout.fillWidth: true
                QQC2.Button {
                    text: qsTr("Global Theme settings")
                    icon.name: "preferences-desktop-theme-global"
                    onClicked: backend.launch("globaltheme")
                }
                QQC2.Button {
                    text: qsTr("Colours")
                    icon.name: "preferences-desktop-color"
                    onClicked: backend.launch("colors")
                }
                Item { Layout.fillWidth: true }
                QQC2.Button {
                    text: logArea.visible ? qsTr("Hide log") : qsTr("Log")
                    icon.name: "view-list-text"
                    onClicked: logArea.visible = !logArea.visible
                }
            }

            QQC2.TextArea {
                id: logArea
                Layout.fillWidth: true
                Layout.preferredHeight: Kirigami.Units.gridUnit * 10
                visible: false
                readOnly: true
                font.family: "monospace"
                wrapMode: TextEdit.NoWrap
            }
        }
    }

    Dialogs.ColorDialog {
        id: colorDialog
        selectedColor: root.pendingAccent
        onAccepted: {
            root.pendingAccent = selectedColor.toString();
            if (root.pendingName === "Borealis") {
                root.pendingName = qsTr("Borealis Custom");
            }
        }
    }

    Connections {
        target: backend
        function onLogged(line) {
            logArea.text += line + "\n";
            logArea.cursorPosition = logArea.length;
        }
        function onFinished(ok, message) {
            root.showPassiveNotification(message, ok ? 6000 : 12000);
            if (!ok) {
                logArea.visible = true;
            }
        }
    }
}
