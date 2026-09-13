/*
    Borealis Tweaks, the Touchpad & Keys page: the touchpad (KWin applies and
    keeps each change at once) and the shortcuts people most often change.
    SPDX-License-Identifier: GPL-3.0-or-later
*/
import QtQuick
import QtQuick.Controls as QQC2
import QtQuick.Layouts
import org.kde.kirigami as Kirigami
import org.kde.kquickcontrols as KQuickControls
import "../controls"

Kirigami.ScrollablePage {
    id: page
    title: qsTr("Touchpad & Keys")

    readonly property var v: inputSettings.values
    readonly property bool pad: (v.touchpad || "") !== ""
    readonly property var scrollFactors: [0.1, 0.3, 0.5, 0.75, 1, 1.5, 2, 3, 4, 5, 7, 9, 12, 15, 20]

    component PadToggle: Toggle {
        target: inputSettings
    }
    component PadChoice: Choice {
        target: inputSettings
    }
    component PadAmount: Amount {
        target: inputSettings
    }

    Connections {
        target: inputSettings
        function onNotice(text) {
            applicationWindow().showPassiveNotification(text, 8000);
        }
    }

    ColumnLayout {
        spacing: Kirigami.Units.largeSpacing

        Kirigami.InlineMessage {
            Layout.fillWidth: true
            visible: !page.pad
            type: Kirigami.MessageType.Information
            text: qsTr("No touchpad was found, so only the shortcuts are here.")
        }

        Kirigami.FormLayout {
            Layout.fillWidth: true

            Kirigami.Separator {
                visible: page.pad
                Kirigami.FormData.isSection: true
                Kirigami.FormData.label: qsTr("Touchpad")
            }
            QQC2.Label {
                visible: page.pad
                Kirigami.FormData.label: qsTr("Device:")
                text: page.v.touchpad || ""
                opacity: 0.7
            }
            PadToggle {
                visible: page.pad && page.v.canTap === true
                Kirigami.FormData.label: qsTr("Tap to click:")
                key: "tapToClick"
            }
            PadToggle {
                visible: page.pad && page.v.canTap === true
                enabled: page.v.tapToClick === true
                Kirigami.FormData.label: qsTr("Tap and drag:")
                key: "tapAndDrag"
            }
            PadToggle {
                visible: page.pad && page.v.canTap === true
                enabled: page.v.tapToClick === true && page.v.tapAndDrag === true
                Kirigami.FormData.label: qsTr("Drag lock:")
                key: "tapDragLock"
            }
            PadChoice {
                visible: page.pad && page.v.canTap === true && page.v.canTwoFingerTap === true
                enabled: page.v.tapToClick === true
                Kirigami.FormData.label: qsTr("Two-finger tap:")
                key: "twoFingerTap"
                choices: [["right", qsTr("Right-click")], ["middle", qsTr("Middle-click")]]
            }
            PadChoice {
                visible: page.pad && page.v.canRightClick === true
                Kirigami.FormData.label: qsTr("Right-click by pressing:")
                key: "rightClick"
                choices: [["corner", qsTr("The bottom-right corner")], ["twoFingers", qsTr("With two fingers")]]
            }
            Hint {
                visible: page.pad && page.v.canRightClick === true
                text: page.v.rightClick === "corner"
                    ? qsTr("A press with two fingers anywhere else is a left click.")
                    : qsTr("Pressing anywhere with two fingers right-clicks, three fingers middle-click.")
            }
            PadToggle {
                visible: page.pad && page.v.can_middleEmulation === true
                Kirigami.FormData.label: qsTr("Middle-click with both corners:")
                key: "middleEmulation"
            }

            Kirigami.Separator {
                visible: page.pad
            }
            PadAmount {
                visible: page.pad && page.v.canAccelerate === true
                Kirigami.FormData.label: qsTr("Pointer speed:")
                key: "pointerSpeed"
                from: -100
                to: 100
                describe: value => Math.round(value) > 0 ? qsTr("+%1").arg(Math.round(value)) : String(Math.round(value))
            }
            PadToggle {
                visible: page.pad && page.v.canAccelerate === true
                Kirigami.FormData.label: qsTr("Faster when moved fast:")
                key: "acceleration"
            }
            PadChoice {
                visible: page.pad && page.v.canScrollMethod === true
                Kirigami.FormData.label: qsTr("Scroll with:")
                key: "scrollMethod"
                choices: [["twoFingers", qsTr("Two fingers")], ["edge", qsTr("One finger at the edge")]]
            }
            PadAmount {
                visible: page.pad
                Kirigami.FormData.label: qsTr("Scroll speed:")
                key: "scrollSpeed"
                from: 0
                to: 14
                describe: value => qsTr("%1×").arg(page.scrollFactors[Math.max(0, Math.min(14, Math.round(value)))])
            }
            PadToggle {
                visible: page.pad && page.v.can_naturalScroll === true
                Kirigami.FormData.label: qsTr("Natural scrolling:")
                key: "naturalScroll"
            }
            PadToggle {
                visible: page.pad && page.v.can_disableWhileTyping === true
                Kirigami.FormData.label: qsTr("Off while typing:")
                key: "disableWhileTyping"
            }
            PadToggle {
                visible: page.pad && page.v.can_disableWithMouse === true
                Kirigami.FormData.label: qsTr("Off with a mouse plugged in:")
                key: "disableWithMouse"
            }
            PadToggle {
                visible: page.pad && page.v.can_leftHanded === true
                Kirigami.FormData.label: qsTr("Left-handed:")
                key: "leftHanded"
            }
            QQC2.Button {
                visible: page.pad
                text: qsTr("Reset the touchpad")
                icon.name: "edit-undo"
                onClicked: inputSettings.resetTouchpad()
            }

            Kirigami.Separator {
                Kirigami.FormData.isSection: true
                Kirigami.FormData.label: qsTr("Shortcuts")
            }
            PadToggle {
                visible: page.v.hasLaunchpad === true
                Kirigami.FormData.label: qsTr("A tap of Meta opens Launchpad:")
                key: "launchpadMeta"
            }
            Repeater {
                model: page.v.shortcuts || []
                delegate: RowLayout {
                    id: shortcutRow
                    required property var modelData
                    Kirigami.FormData.label: modelData.label + ":"
                    spacing: Kirigami.Units.smallSpacing

                    KQuickControls.KeySequenceItem {
                        keySequence: shortcutRow.modelData.key
                        modifierlessAllowed: false
                        multiKeyShortcutsAllowed: false
                        checkForConflictsAgainst: KQuickControls.ShortcutType.None
                        onKeySequenceModified: inputSettings.setShortcut(shortcutRow.modelData.id, keySequence)
                    }
                    QQC2.ToolButton {
                        visible: !shortcutRow.modelData.isDefault
                        icon.name: "edit-undo"
                        display: QQC2.AbstractButton.IconOnly
                        text: qsTr("Back to the usual key")
                        QQC2.ToolTip.text: text
                        QQC2.ToolTip.visible: hovered
                        onClicked: inputSettings.resetShortcut(shortcutRow.modelData.id)
                    }
                    QQC2.Label {
                        visible: shortcutRow.modelData.others !== ""
                        text: qsTr("and %1").arg(shortcutRow.modelData.others)
                        opacity: 0.6
                        elide: Text.ElideRight
                        Layout.maximumWidth: Kirigami.Units.gridUnit * 10
                    }
                }
            }
            QQC2.Button {
                text: qsTr("Every shortcut…")
                icon.name: "preferences-desktop-keyboard-shortcut"
                onClicked: dockSettings.openShortcuts()
            }
        }
    }
}
