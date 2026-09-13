/*
    Borealis Tweaks, the Desktop page: virtual desktops, hot corners and screen
    edges, night light, and how files open.
    SPDX-License-Identifier: GPL-3.0-or-later
*/
import QtQuick
import QtQuick.Controls as QQC2
import QtQuick.Layouts
import org.kde.kirigami as Kirigami
import "../controls"

Kirigami.ScrollablePage {
    id: page
    title: qsTr("Desktop")

    readonly property var v: desktopSettings.values
    readonly property var cornerChoices: [
        ["none", qsTr("Nothing")], ["overview", qsTr("Overview")], ["grid", qsTr("All desktops")],
        ["windows", qsTr("All windows")], ["desktop", qsTr("Peek at the desktop")], ["lock", qsTr("Lock the screen")],
        ["search", qsTr("Search")]
    ]

    component DeskToggle: Toggle {
        target: desktopSettings
    }
    component DeskChoice: Choice {
        target: desktopSettings
    }
    component DeskAmount: Amount {
        target: desktopSettings
    }
    // a time of day, typed as 18:30
    component TimeField: QQC2.TextField {
        required property string key
        text: page.v[key] || ""
        inputMask: "99:99"
        validator: RegularExpressionValidator {
            regularExpression: /^([01][0-9]|2[0-3]):[0-5][0-9]$/
        }
        Layout.preferredWidth: Kirigami.Units.gridUnit * 4
        onEditingFinished: if (acceptableInput && text !== page.v[key]) {
            desktopSettings.set(key, text);
        }
    }

    ColumnLayout {
        spacing: Kirigami.Units.largeSpacing

        Kirigami.FormLayout {
            Layout.fillWidth: true

            Kirigami.Separator {
                Kirigami.FormData.isSection: true
                Kirigami.FormData.label: qsTr("Virtual desktops")
            }
            QQC2.SpinBox {
                Kirigami.FormData.label: qsTr("How many:")
                from: 1
                to: 12
                value: page.v.desktopCount || 1
                onValueModified: desktopSettings.set("desktopCount", value)
            }
            QQC2.SpinBox {
                Kirigami.FormData.label: qsTr("Rows:")
                enabled: (page.v.desktopCount || 1) > 1
                from: 1
                to: 4
                value: page.v.rows || 1
                onValueModified: desktopSettings.set("rows", value)
            }
            Repeater {
                model: page.v.desktops || []
                delegate: QQC2.TextField {
                    required property var modelData
                    required property int index
                    Kirigami.FormData.label: index === 0 ? qsTr("Names:") : ""
                    text: modelData.name
                    onEditingFinished: if (text !== modelData.name) {
                        desktopSettings.renameDesktop(modelData.id, text);
                    }
                }
            }
            DeskToggle {
                Kirigami.FormData.label: qsTr("Wrap around:")
                enabled: (page.v.desktopCount || 1) > 1
                key: "wrapAround"
            }
            Hint {
                text: qsTr("Meta+Ctrl+Left and Right move between desktops, and the Overview shows them all.")
            }

            Kirigami.Separator {
                Kirigami.FormData.isSection: true
                Kirigami.FormData.label: qsTr("Hot corners")
            }
            DeskChoice {
                Kirigami.FormData.label: qsTr("Top left:")
                key: "topLeft"
                choices: page.cornerChoices
            }
            DeskChoice {
                Kirigami.FormData.label: qsTr("Top right:")
                key: "topRight"
                choices: page.cornerChoices
            }
            DeskChoice {
                Kirigami.FormData.label: qsTr("Bottom left:")
                key: "bottomLeft"
                choices: page.cornerChoices
            }
            DeskChoice {
                Kirigami.FormData.label: qsTr("Bottom right:")
                key: "bottomRight"
                choices: page.cornerChoices
            }
            DeskChoice {
                Kirigami.FormData.label: qsTr("Screen edges:")
                key: "edgeSwitch"
                choices: [[0, qsTr("Do nothing")], [1, qsTr("Switch desktops when a window is dragged there")],
                          [2, qsTr("Always switch desktops")]]
            }
            Hint {
                text: qsTr("Push the pointer into a corner to use it; the bar and the dock don't get in the way.")
            }
            QQC2.Button {
                text: qsTr("Reset corners and edges")
                icon.name: "edit-undo"
                onClicked: desktopSettings.resetCorners()
            }

            Kirigami.Separator {
                Kirigami.FormData.isSection: true
                Kirigami.FormData.label: qsTr("Night light")
            }
            DeskChoice {
                Kirigami.FormData.label: qsTr("Night light:")
                key: "nightLight"
                choices: [["off", qsTr("Off")], ["sunset", qsTr("From sunset to sunrise")], ["always", qsTr("Always on")]]
            }
            DeskAmount {
                visible: page.v.nightLight !== "off"
                Kirigami.FormData.label: qsTr("Warmth:")
                key: "nightTemperature"
                from: 1000
                to: 6500
                stepSize: 100
                describe: value => qsTr("%1 K").arg(Math.round(value / 100) * 100)
            }
            DeskChoice {
                visible: page.v.nightLight === "sunset"
                Kirigami.FormData.label: qsTr("Sunset and sunrise:")
                key: "nightSchedule"
                choices: [["location", qsTr("Where you are")], ["times", qsTr("At times you set")]]
            }
            RowLayout {
                visible: page.v.nightLight === "sunset" && page.v.nightSchedule === "times"
                Kirigami.FormData.label: qsTr("Warm from:")
                spacing: Kirigami.Units.smallSpacing
                TimeField {
                    key: "sunset"
                }
                QQC2.Label {
                    text: qsTr("until")
                }
                TimeField {
                    key: "sunrise"
                }
            }
            QQC2.Button {
                text: qsTr("Reset night light")
                icon.name: "edit-undo"
                onClicked: desktopSettings.resetNightLight()
            }

            Kirigami.Separator {
                Kirigami.FormData.isSection: true
                Kirigami.FormData.label: qsTr("Files")
            }
            DeskChoice {
                Kirigami.FormData.label: qsTr("Open files and folders with:")
                key: "singleClick"
                choices: [[false, qsTr("A double click")], [true, qsTr("A single click")]]
            }
        }
    }
}
