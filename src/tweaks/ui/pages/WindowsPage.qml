/*
    Borealis Tweaks, the Windows page: the title bar's buttons, window corners,
    blur and how fast things animate. Changes apply as you make them; the
    corners after a short rebuild of the window decoration.
    SPDX-License-Identifier: GPL-3.0-or-later
*/
import QtQuick
import QtQuick.Controls as QQC2
import QtQuick.Layouts
import org.kde.kirigami as Kirigami
import "../controls"

Kirigami.ScrollablePage {
    id: page
    title: qsTr("Windows")

    readonly property var v: windowsSettings.values
    readonly property int appliedRadius: v.cornerRadius !== undefined ? v.cornerRadius : 12
    property int radiusDraft: appliedRadius
    onAppliedRadiusChanged: radiusDraft = appliedRadius

    component WinToggle: Toggle {
        target: windowsSettings
    }
    component WinChoice: Choice {
        target: windowsSettings
    }
    component WinAmount: Amount {
        target: windowsSettings
    }

    // a row of title bar buttons, drawn as Borealis draws them
    component PreviewButtons: Row {
        id: buttonRow
        property var names: []
        readonly property color ink: Kirigami.Theme.textColor
        readonly property var pillColors: ({
            close: Kirigami.Theme.negativeTextColor, minimize: Kirigami.Theme.positiveTextColor,
            maximize: Kirigami.Theme.highlightColor
        })
        spacing: 10
        Repeater {
            model: buttonRow.names
            delegate: Item {
                id: button
                required property string modelData
                width: modelData === "appIcon" ? 16 : 18
                height: 16
                Rectangle {
                    visible: button.modelData !== "appIcon"
                    anchors.centerIn: parent
                    width: 18
                    height: 8
                    radius: 4
                    color: buttonRow.pillColors[button.modelData]
                        || Qt.rgba(buttonRow.ink.r, buttonRow.ink.g, buttonRow.ink.b, 0.35)
                }
                Kirigami.Icon {
                    visible: button.modelData === "appIcon"
                    anchors.fill: parent
                    source: "preferences-system-windows"
                }
            }
        }
    }

    // a title bar laid out the way the choices below would have it
    component TitleBarPreview: Item {
        id: preview
        readonly property color ink: Kirigami.Theme.textColor
        readonly property bool leftSide: page.v.buttonsSide === "left"
        readonly property var order: leftSide ? ["close", "minimize", "maximize", "allDesktops", "keepAbove"]
                                              : ["keepAbove", "allDesktops", "minimize", "maximize", "close"]
        readonly property var buttons: order.filter(name => page.v[name] === true)
        implicitHeight: Kirigami.Units.gridUnit * 6

        Rectangle {
            id: frame
            anchors.fill: parent
            anchors.margins: Kirigami.Units.largeSpacing
            radius: Math.min(page.radiusDraft, height / 2)
            color: Qt.rgba(preview.ink.r, preview.ink.g, preview.ink.b, 0.08)
            border.width: 1
            border.color: Qt.rgba(preview.ink.r, preview.ink.g, preview.ink.b, 0.22)

            PreviewButtons {
                anchors.left: parent.left
                anchors.leftMargin: 14
                y: 12
                names: preview.leftSide ? preview.buttons : (page.v.appIcon ? ["appIcon"] : [])
            }
            QQC2.Label {
                anchors.horizontalCenter: parent.horizontalCenter
                y: 10
                text: qsTr("A window")
                font.weight: Font.DemiBold
            }
            PreviewButtons {
                anchors.right: parent.right
                anchors.rightMargin: 14
                y: 12
                names: preview.leftSide ? (page.v.appIcon ? ["appIcon"] : []) : preview.buttons
            }
            Rectangle {
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.bottom: parent.bottom
                anchors.margins: 1
                anchors.topMargin: 0
                height: parent.height - 38
                radius: Math.min(4, page.radiusDraft)
                color: Kirigami.Theme.backgroundColor
            }
        }
    }

    ColumnLayout {
        spacing: Kirigami.Units.largeSpacing

        TitleBarPreview {
            Layout.fillWidth: true
            Layout.maximumWidth: Kirigami.Units.gridUnit * 26
            Layout.alignment: Qt.AlignHCenter
        }

        Kirigami.FormLayout {
            Layout.fillWidth: true

            Kirigami.Separator {
                Kirigami.FormData.isSection: true
                Kirigami.FormData.label: qsTr("Title bar")
            }
            WinChoice {
                Kirigami.FormData.label: qsTr("Buttons:")
                key: "buttonsSide"
                choices: [["right", qsTr("At the right")], ["left", qsTr("At the left, close first")]]
            }
            WinToggle {
                Kirigami.FormData.label: qsTr("Minimize:")
                key: "minimize"
            }
            WinToggle {
                Kirigami.FormData.label: qsTr("Maximize:")
                key: "maximize"
            }
            WinToggle {
                Kirigami.FormData.label: qsTr("Close:")
                key: "close"
            }
            WinToggle {
                Kirigami.FormData.label: qsTr("Keep above others:")
                key: "keepAbove"
            }
            WinToggle {
                Kirigami.FormData.label: qsTr("On all desktops:")
                key: "allDesktops"
            }
            WinToggle {
                Kirigami.FormData.label: qsTr("App icon, opposite:")
                key: "appIcon"
            }
            QQC2.Button {
                text: qsTr("Reset the title bar")
                icon.name: "edit-undo"
                onClicked: windowsSettings.resetTitleBar()
            }

            Kirigami.Separator {
                Kirigami.FormData.isSection: true
                Kirigami.FormData.label: qsTr("Corners")
            }
            RowLayout {
                Kirigami.FormData.label: qsTr("Window corners:")
                enabled: page.v.decoration !== "" && backend.hasProject && !backend.busy
                spacing: Kirigami.Units.largeSpacing
                QQC2.Slider {
                    id: radiusSlider
                    Layout.fillWidth: true
                    Layout.minimumWidth: Kirigami.Units.gridUnit * 6
                    Layout.maximumWidth: Kirigami.Units.gridUnit * 14
                    from: 0
                    to: 24
                    stepSize: 1
                    snapMode: QQC2.Slider.SnapAlways
                    value: page.radiusDraft
                    onMoved: page.radiusDraft = Math.round(value)
                }
                QQC2.Label {
                    Layout.minimumWidth: Kirigami.Units.gridUnit * 3
                    horizontalAlignment: Text.AlignRight
                    font.features: { "tnum": 1 }
                    text: qsTr("%1 px").arg(page.radiusDraft)
                }
                QQC2.Button {
                    text: qsTr("Apply")
                    enabled: page.radiusDraft !== page.appliedRadius
                    onClicked: windowsSettings.applyCornerRadius(page.radiusDraft)
                }
            }
            Hint {
                text: page.v.decoration === "" ? qsTr("Only the Borealis window decoration can change its corners.")
                    : !backend.hasProject ? qsTr("Needs the Borealis project folder, to rebuild the decoration.")
                    : qsTr("The decoration is rebuilt with the new corners, which takes a few seconds. Borealis uses 12 px.")
            }

            Kirigami.Separator {
                Kirigami.FormData.isSection: true
                Kirigami.FormData.label: qsTr("Effects")
            }
            WinAmount {
                Kirigami.FormData.label: qsTr("Blur behind glass:")
                key: "blurStrength"
                from: 1
                to: 15
                describe: value => qsTr("%1 of 15").arg(Math.round(value))
            }
            WinAmount {
                Kirigami.FormData.label: qsTr("Grain in the blur:")
                key: "noiseStrength"
                from: 0
                to: 14
                describe: value => Math.round(value) === 0 ? qsTr("None") : qsTr("%1 of 14").arg(Math.round(value))
            }
            WinAmount {
                Kirigami.FormData.label: qsTr("Animation speed:")
                key: "animationSpeed"
                from: 0
                to: 6
                describe: value => [qsTr("Slowest"), qsTr("Slow"), qsTr("Relaxed"), qsTr("Normal"), qsTr("Brisk"),
                                    qsTr("Fast"), qsTr("Instant")][Math.max(0, Math.min(6, Math.round(value)))]
            }
            QQC2.Button {
                text: qsTr("Reset effects")
                icon.name: "edit-undo"
                onClicked: windowsSettings.resetEffects()
            }
        }

        JobLog {}
    }
}
