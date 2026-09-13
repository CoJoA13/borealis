/*
    Borealis Tweaks, the Bar page: the top bar's look, what sits where, the
    clock, notifications, the Control Center's toggles and the tray.
    Changes reach the running bar as you make them.
    SPDX-License-Identifier: GPL-3.0-or-later
*/
import QtQuick
import QtQuick.Controls as QQC2
import QtQuick.Layouts
import org.kde.kirigami as Kirigami
import "../controls"

Kirigami.ScrollablePage {
    id: page
    title: qsTr("Bar")

    readonly property var itemNames: ({
        menu: qsTr("Borealis menu"), app: qsTr("App name"), appmenu: qsTr("App menus"), clock: qsTr("Clock"),
        tray: qsTr("Tray icons"), drives: qsTr("Drives"), controls: qsTr("Control Center")
    })
    readonly property var pillNames: ({
        wifi: qsTr("Wi-Fi"), bluetooth: qsTr("Bluetooth"), night: qsTr("Night Light"), power: qsTr("Power profile"),
        dark: qsTr("Dark style"), dnd: qsTr("Do Not Disturb"), aurora: qsTr("Aurora wallpaper")
    })
    readonly property var zones: [["left", qsTr("Left")], ["center", qsTr("Middle")], ["right", qsTr("Right")],
                                  ["", qsTr("Hidden")]]

    component BarAmount: Amount {
        target: barSettings
    }
    component BarChoice: Choice {
        target: barSettings
    }
    component BarToggle: Toggle {
        target: barSettings
    }

    ColumnLayout {
        spacing: Kirigami.Units.largeSpacing

        Kirigami.InlineMessage {
            Layout.fillWidth: true
            visible: !barSettings.installed
            type: Kirigami.MessageType.Information
            text: qsTr("You're using a Plasma panel at the top. The Borealis Bar has the app's menus, the clock with your notifications and calendar, the tray and a Control Center, all set up on this page.")
            actions: [
                Kirigami.Action {
                    text: qsTr("Switch to it")
                    icon.name: "dialog-ok-apply"
                    enabled: barSettings.canSwitch && !backend.busy
                    onTriggered: barSettings.enable()
                }
            ]
        }

        Kirigami.InlineMessage {
            Layout.fillWidth: true
            visible: barSettings.installed && !barSettings.running
            type: Kirigami.MessageType.Warning
            text: qsTr("The bar isn't running.")
            actions: [
                Kirigami.Action {
                    text: qsTr("Start it")
                    icon.name: "media-playback-start"
                    onTriggered: barSettings.restart()
                }
            ]
        }

        Kirigami.FormLayout {
            Layout.fillWidth: true

            Kirigami.Separator {
                Kirigami.FormData.isSection: true
                Kirigami.FormData.label: qsTr("Look")
            }
            BarToggle {
                Kirigami.FormData.label: qsTr("Floating:")
                key: "floating"
            }
            BarAmount {
                Kirigami.FormData.label: qsTr("Gap around it:")
                visible: barSettings.values.floating === true
                key: "gap"
                to: 24
                describe: value => qsTr("%1 px").arg(Math.round(value))
            }
            BarToggle {
                Kirigami.FormData.label: qsTr("Flush over maximized windows:")
                visible: barSettings.values.floating === true
                key: "flush"
            }
            BarAmount {
                Kirigami.FormData.label: qsTr("Height:")
                key: "height"
                from: 22
                to: 48
                describe: value => qsTr("%1 px").arg(Math.round(value))
            }
            BarAmount {
                Kirigami.FormData.label: qsTr("Corners:")
                visible: barSettings.values.floating === true
                key: "radius"
                to: 24
                describe: value => qsTr("%1 px").arg(Math.round(value))
            }
            BarAmount {
                Kirigami.FormData.label: qsTr("Background:")
                key: "opacity"
                to: 1
                stepSize: 0.02
                describe: value => qsTr("%1%").arg(Math.round(value * 100))
            }
            BarToggle {
                Kirigami.FormData.label: qsTr("Frosted glass:")
                key: "blur"
            }
            BarToggle {
                Kirigami.FormData.label: qsTr("Outline:")
                key: "border"
            }
            BarChoice {
                Kirigami.FormData.label: qsTr("Show on:")
                key: "screen"
                choices: [["all", qsTr("Every screen")], ["primary", qsTr("The primary screen")]]
            }

            Kirigami.Separator {
                Kirigami.FormData.isSection: true
                Kirigami.FormData.label: qsTr("What goes where")
            }
            Repeater {
                model: barSettings.items
                delegate: RowLayout {
                    id: itemRow
                    required property string modelData
                    required property int index
                    readonly property string zone: {
                        const v = barSettings.values;
                        return (v.left || []).indexOf(modelData) >= 0 ? "left"
                            : (v.center || []).indexOf(modelData) >= 0 ? "center"
                            : (v.right || []).indexOf(modelData) >= 0 ? "right" : "";
                    }
                    Kirigami.FormData.label: page.itemNames[modelData] + ":"
                    QQC2.ComboBox {
                        model: page.zones.map(z => z[1])
                        implicitContentWidthPolicy: QQC2.ComboBox.WidestText
                        currentIndex: page.zones.findIndex(z => z[0] === itemRow.zone)
                        onActivated: i => barSettings.placeItem(itemRow.modelData, page.zones[i][0])
                    }
                    QQC2.ToolButton {
                        icon.name: "go-previous"
                        enabled: itemRow.zone !== ""
                        QQC2.ToolTip.text: qsTr("Earlier in its part of the bar")
                        QQC2.ToolTip.visible: hovered
                        onClicked: barSettings.moveItem(itemRow.modelData, -1)
                    }
                    QQC2.ToolButton {
                        icon.name: "go-next"
                        enabled: itemRow.zone !== ""
                        QQC2.ToolTip.text: qsTr("Later in its part of the bar")
                        QQC2.ToolTip.visible: hovered
                        onClicked: barSettings.moveItem(itemRow.modelData, 1)
                    }
                }
            }

            Kirigami.Separator {
                Kirigami.FormData.isSection: true
                Kirigami.FormData.label: qsTr("Clock")
            }
            BarToggle {
                Kirigami.FormData.label: qsTr("Day of the week:")
                key: "clockWeekday"
            }
            BarToggle {
                Kirigami.FormData.label: qsTr("Date:")
                key: "clockDate"
            }
            BarToggle {
                Kirigami.FormData.label: qsTr("Seconds:")
                key: "clockSeconds"
            }
            BarChoice {
                Kirigami.FormData.label: qsTr("Hours:")
                key: "clockHours"
                choices: [["auto", qsTr("As your region shows them")], ["24", qsTr("24-hour")], ["12", qsTr("12-hour")]]
            }

            Kirigami.Separator {
                Kirigami.FormData.isSection: true
                Kirigami.FormData.label: qsTr("Notifications")
            }
            BarToggle {
                Kirigami.FormData.label: qsTr("Pop up under the bar:")
                key: "banners"
            }
            BarChoice {
                Kirigami.FormData.label: qsTr("Where:")
                visible: barSettings.values.banners === true
                key: "bannerPosition"
                choices: [["right", qsTr("Top right")], ["center", qsTr("Top middle")]]
            }
            QQC2.Button {
                Kirigami.FormData.label: qsTr("Per app:")
                text: qsTr("Notification settings…")
                icon.name: "preferences-desktop-notification-bell"
                onClicked: barSettings.openKcm("kcm_notifications")
            }

            Kirigami.Separator {
                Kirigami.FormData.isSection: true
                Kirigami.FormData.label: qsTr("Control Center")
            }
            Repeater {
                model: barSettings.pills
                delegate: RowLayout {
                    id: pillRow
                    required property string modelData
                    readonly property bool on: (barSettings.values.pills || []).indexOf(modelData) >= 0
                    Kirigami.FormData.label: page.pillNames[modelData] + ":"
                    QQC2.Switch {
                        checked: pillRow.on
                        onToggled: {
                            barSettings.setPill(pillRow.modelData, checked);
                            checked = Qt.binding(() => pillRow.on);
                        }
                    }
                    QQC2.ToolButton {
                        icon.name: "go-up"
                        enabled: pillRow.on
                        QQC2.ToolTip.text: qsTr("Earlier")
                        QQC2.ToolTip.visible: hovered
                        onClicked: barSettings.movePill(pillRow.modelData, -1)
                    }
                    QQC2.ToolButton {
                        icon.name: "go-down"
                        enabled: pillRow.on
                        QQC2.ToolTip.text: qsTr("Later")
                        QQC2.ToolTip.visible: hovered
                        onClicked: barSettings.movePill(pillRow.modelData, 1)
                    }
                }
            }
            BarToggle {
                Kirigami.FormData.label: qsTr("What's playing:")
                key: "media"
            }

            Kirigami.Separator {
                Kirigami.FormData.isSection: true
                Kirigami.FormData.label: qsTr("Tray")
            }
            QQC2.Label {
                Kirigami.FormData.label: qsTr("Icons:")
                visible: barSettings.trayItems.length === 0
                text: barSettings.running ? qsTr("No app has a tray icon right now") : qsTr("Shown while the bar runs")
                opacity: 0.7
            }
            Repeater {
                model: barSettings.trayItems
                delegate: QQC2.Switch {
                    required property var modelData
                    required property int index
                    Kirigami.FormData.label: index === 0 ? qsTr("Icons:") : ""
                    text: modelData.title || modelData.id
                    checked: (barSettings.values.trayHidden || []).indexOf(modelData.id) < 0
                    onToggled: {
                        barSettings.setTrayShown(modelData.id, checked);
                        checked = Qt.binding(() => (barSettings.values.trayHidden || []).indexOf(modelData.id) < 0);
                    }
                }
            }
        }

        Kirigami.Separator {
            Layout.fillWidth: true
        }

        Flow {
            Layout.fillWidth: true
            spacing: Kirigami.Units.smallSpacing
            QQC2.Button {
                text: qsTr("Reset the bar's look")
                icon.name: "edit-undo"
                onClicked: barSettings.resetLook()
            }
            QQC2.Button {
                visible: barSettings.installed
                text: qsTr("Restart the bar")
                icon.name: "view-refresh"
                onClicked: barSettings.restart()
            }
            QQC2.Button {
                visible: barSettings.installed && barSettings.canSwitch
                enabled: !backend.busy
                text: qsTr("Back to a Plasma panel")
                icon.name: "go-previous"
                onClicked: barSettings.disable()
            }
        }

        QQC2.Label {
            Layout.fillWidth: true
            wrapMode: Text.WrapAnywhere
            opacity: 0.6
            font: Kirigami.Theme.smallFont
            text: qsTr("Settings file: %1").arg(barSettings.configPath)
        }

        JobLog {}
    }
}
