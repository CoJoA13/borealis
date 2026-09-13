/*
    Borealis Tweaks, the Theme page: light or dark, the animated wallpaper, and
    remixing the palette onto another colour.
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

    title: qsTr("Theme")

    property string pendingAccent: backend.accent
    property string pendingName: backend.paletteName

    header: Kirigami.InlineMessage {
        visible: !backend.isBorealis
        position: Kirigami.InlineMessage.Header
        type: Kirigami.MessageType.Information
        text: qsTr("The current Global Theme is “%1”. Applying anything here switches to Borealis.")
                  .arg(backend.themeName)
    }

    ColumnLayout {
        spacing: Kirigami.Units.largeSpacing

        // -------------------------------------------------------- variant --
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

        Kirigami.Separator {
            Layout.fillWidth: true
        }

        // ---------------------------------------------------------- remix --
        Kirigami.Heading {
            level: 3
            text: qsTr("Remix the palette")
        }
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
                        page.pendingAccent = modelData.color;
                        page.pendingName = modelData.name === "Nocturne" ? "Borealis" : "Borealis " + modelData.name;
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
                            border.width: page.pendingAccent === modelData.color ? 3 : 1
                            border.color: page.pendingAccent === modelData.color
                                          ? Kirigami.Theme.textColor
                                          : Qt.rgba(Kirigami.Theme.textColor.r, Kirigami.Theme.textColor.g,
                                                    Kirigami.Theme.textColor.b, 0.3)
                        }
                        QQC2.Label {
                            text: modelData.name
                            elide: Text.ElideRight
                            Layout.fillWidth: true
                        }
                    }
                }
            }
        }

        Flow {
            Layout.fillWidth: true
            spacing: Kirigami.Units.smallSpacing
            QQC2.Button {
                text: qsTr("Custom colour…")
                icon.name: "color-picker"
                enabled: backend.hasProject && !backend.busy
                onClicked: colorDialog.open()
            }
            QQC2.TextField {
                width: Kirigami.Units.gridUnit * 14
                placeholderText: qsTr("Name for this remix")
                text: page.pendingName
                enabled: backend.hasProject && !backend.busy
                onTextEdited: page.pendingName = text
            }
        }

        RowLayout {
            Layout.fillWidth: true
            QQC2.CheckBox {
                id: gtkBox
                text: qsTr("GTK apps")
                checked: true
                enabled: !backend.busy
            }
            QQC2.CheckBox {
                id: termBox
                text: qsTr("Terminal")
                checked: true
                enabled: !backend.busy
            }
            Item {
                Layout.fillWidth: true
            }
            QQC2.Button {
                text: backend.busy ? qsTr("Working…") : qsTr("Apply palette")
                icon.name: "dialog-ok-apply"
                enabled: backend.hasProject && !backend.busy && page.pendingName.length > 0
                onClicked: backend.remix(page.pendingAccent, page.pendingName.trim(), gtkBox.checked, termBox.checked)
            }
        }

        Kirigami.Separator {
            Layout.fillWidth: true
        }

        Flow {
            Layout.fillWidth: true
            spacing: Kirigami.Units.smallSpacing
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
        }

        JobLog {}
    }

    Dialogs.ColorDialog {
        id: colorDialog
        selectedColor: page.pendingAccent
        onAccepted: {
            page.pendingAccent = selectedColor.toString();
            if (page.pendingName === "Borealis") {
                page.pendingName = qsTr("Borealis Custom");
            }
        }
    }
}
