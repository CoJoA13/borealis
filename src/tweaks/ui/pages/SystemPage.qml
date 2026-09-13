/*
    Borealis Tweaks, the System page: the parts of Borealis outside Plasma
    (login screen, boot, fonts, GTK and Firefox, the terminal) and undo.
    SPDX-License-Identifier: GPL-3.0-or-later
*/
import QtQuick
import QtQuick.Controls as QQC2
import QtQuick.Layouts
import org.kde.kirigami as Kirigami
import "../controls"

Kirigami.ScrollablePage {
    id: page
    title: qsTr("System")

    // a status line with its buttons beside it
    component Status: RowLayout {
        property alias text: statusLabel.text
        property bool good: false
        spacing: Kirigami.Units.smallSpacing
        Kirigami.Icon {
            source: parent.good ? "emblem-ok-symbolic" : "emblem-warning"
            Layout.preferredWidth: Kirigami.Units.iconSizes.small
            Layout.preferredHeight: Kirigami.Units.iconSizes.small
        }
        QQC2.Label {
            id: statusLabel
        }
    }

    ColumnLayout {
        spacing: Kirigami.Units.largeSpacing

        Kirigami.InlineMessage {
            Layout.fillWidth: true
            visible: !backend.hasProject
            type: Kirigami.MessageType.Information
            text: qsTr("The Borealis project folder was not found, so the installers on this page are unavailable. Set BOREALIS_PROJECT to its path.")
        }

        Kirigami.FormLayout {
            Layout.fillWidth: true

            // ------------------------------------------------ login and boot --
            Kirigami.Separator {
                Kirigami.FormData.isSection: true
                Kirigami.FormData.label: qsTr("Login and start-up")
            }
            Status {
                Kirigami.FormData.label: qsTr("Login screen:")
                good: backend.systemWide
                text: backend.systemWide ? qsTr("Can use Borealis") : qsTr("Can't see Borealis yet")
            }
            Flow {
                Layout.fillWidth: true
                spacing: Kirigami.Units.smallSpacing
                QQC2.Button {
                    visible: !backend.systemWide
                    enabled: backend.hasProject && !backend.busy
                    text: qsTr("Copy system-wide…")
                    icon.name: "system-upgrade"
                    onClicked: backend.installSystemWide("")
                }
                QQC2.Button {
                    text: qsTr("Login screen settings…")
                    icon.name: "preferences-system-login"
                    onClicked: backend.launch("login")
                }
            }
            Hint {
                text: qsTr("The login screen copies your look when you press “Apply Plasma Settings…” on its settings page; Plasma can't do that from here.")
            }

            Status {
                Kirigami.FormData.label: qsTr("Boot splash:")
                good: backend.bootSplash === "borealis"
                text: backend.bootSplash.length ? backend.bootSplash : qsTr("unknown")
            }
            Flow {
                Layout.fillWidth: true
                spacing: Kirigami.Units.smallSpacing
                QQC2.Button {
                    visible: backend.bootSplash !== "borealis"
                    enabled: backend.hasProject && !backend.busy
                    text: qsTr("Use the Borealis splash…")
                    icon.name: "system-reboot"
                    onClicked: backend.installSystemWide("--plymouth")
                }
                QQC2.Button {
                    visible: backend.bootSplash === "borealis"
                    enabled: backend.hasProject && !backend.busy
                    text: qsTr("Put the old splash back…")
                    icon.name: "edit-undo"
                    onClicked: backend.installSystemWide("--plymouth-revert")
                }
            }

            Status {
                Kirigami.FormData.label: qsTr("Boot menu:")
                good: backend.grubMenu
                text: backend.grubMenu ? qsTr("Borealis") : qsTr("Plain text")
            }
            Flow {
                Layout.fillWidth: true
                spacing: Kirigami.Units.smallSpacing
                QQC2.Button {
                    visible: !backend.grubMenu
                    enabled: backend.hasProject && !backend.busy
                    text: qsTr("Use the Borealis boot menu…")
                    icon.name: "system-run"
                    onClicked: backend.installSystemWide("--grub")
                }
                QQC2.Button {
                    visible: backend.grubMenu
                    enabled: backend.hasProject && !backend.busy
                    text: qsTr("Back to the plain menu…")
                    icon.name: "edit-undo"
                    onClicked: backend.installSystemWide("--grub-revert")
                }
            }
            Hint {
                text: qsTr("Buttons ending in “…” ask for your password. Changing the splash rebuilds the initramfs, which takes a minute or two.")
            }

            // ---------------------------------------------------------- fonts --
            Kirigami.Separator {
                Kirigami.FormData.isSection: true
                Kirigami.FormData.label: qsTr("Fonts")
            }
            Status {
                Kirigami.FormData.label: qsTr("Inter and JetBrains Mono:")
                good: backend.fontsInstalled
                text: backend.fontsInstalled ? qsTr("Installed") : qsTr("Missing")
            }
            Flow {
                Layout.fillWidth: true
                spacing: Kirigami.Units.smallSpacing
                QQC2.Button {
                    visible: !backend.fontsInstalled
                    enabled: !backend.busy
                    text: qsTr("Install them…")
                    icon.name: "font-install"
                    onClicked: backend.installFonts()
                }
                QQC2.Button {
                    text: qsTr("Font settings…")
                    icon.name: "preferences-desktop-font"
                    onClicked: backend.launch("fonts")
                }
            }

            // ------------------------------------------------ beyond Plasma --
            Kirigami.Separator {
                Kirigami.FormData.isSection: true
                Kirigami.FormData.label: qsTr("Apps beyond Plasma")
            }
            RowLayout {
                Kirigami.FormData.label: qsTr("GTK apps:")
                Status {
                    good: backend.gtkColors
                    text: backend.gtkColors ? qsTr("Borealis colours") : qsTr("Adwaita grey")
                }
                QQC2.Button {
                    visible: !backend.gtkColors
                    enabled: backend.hasProject && !backend.busy
                    text: qsTr("Colour them")
                    onClicked: backend.installExtra("--gtk")
                }
            }
            RowLayout {
                Kirigami.FormData.label: qsTr("Flatpak apps:")
                visible: backend.hasFlatpak
                Status {
                    good: backend.flatpakColors
                    text: backend.flatpakColors ? qsTr("Can read the colours") : qsTr("Can't read the colours")
                }
                QQC2.Button {
                    visible: !backend.flatpakColors
                    enabled: !backend.busy
                    text: qsTr("Let them")
                    onClicked: backend.grantFlatpakColors()
                }
            }
            RowLayout {
                Kirigami.FormData.label: qsTr("Konsole:")
                Status {
                    good: backend.konsoleDefault
                    text: backend.konsoleDefault ? qsTr("Opens with the Borealis profile") : qsTr("Another profile")
                }
                QQC2.Button {
                    visible: !backend.konsoleDefault
                    enabled: backend.hasProject && !backend.busy
                    text: qsTr("Use Borealis")
                    onClicked: backend.installExtra("--konsole")
                }
            }
            RowLayout {
                Kirigami.FormData.label: qsTr("Command line:")
                Status {
                    good: backend.terminalKit
                    text: backend.terminalKit ? qsTr("Borealis colours") : qsTr("Not styled")
                }
                QQC2.Button {
                    visible: !backend.terminalKit
                    enabled: backend.hasProject && !backend.busy
                    text: qsTr("Style it")
                    onClicked: backend.installExtra("--terminal")
                }
            }
            Hint {
                text: qsTr("Colours for bat, tmux, git, ls and fzf, and a matching prompt in new bash shells.")
            }
            RowLayout {
                Kirigami.FormData.label: qsTr("Firefox:")
                Status {
                    good: backend.firefoxStyled
                    text: !backend.hasFirefox ? qsTr("No profile yet")
                        : backend.firefoxStyled ? qsTr("Borealis window") : qsTr("Not styled")
                }
                QQC2.Button {
                    visible: backend.hasFirefox && !backend.firefoxStyled
                    enabled: backend.hasProject && !backend.busy
                    text: qsTr("Style it")
                    onClicked: backend.installExtra("--firefox")
                }
            }

            // ----------------------------------------------------------- undo --
            Kirigami.Separator {
                Kirigami.FormData.isSection: true
                Kirigami.FormData.label: qsTr("Undo")
            }
            RowLayout {
                Kirigami.FormData.label: qsTr("Backups:")
                QQC2.ComboBox {
                    id: backupBox
                    model: backend.backups
                    implicitContentWidthPolicy: QQC2.ComboBox.WidestText
                    displayText: count ? currentText : qsTr("No backups yet")
                    enabled: count > 0 && !backend.busy
                }
                QQC2.Button {
                    text: qsTr("Restore")
                    icon.name: "edit-undo"
                    enabled: backupBox.count > 0 && !backend.busy && backend.hasProject
                    onClicked: backend.restore(backupBox.currentText)
                }
            }
            Hint {
                text: qsTr("Each theme change, dock switch or install from this page saves the settings it touches first; restoring one puts them back.")
            }
        }

        JobLog {}
    }
}
