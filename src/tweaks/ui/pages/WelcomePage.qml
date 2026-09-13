/*
    Borealis Tweaks, the welcome tour: six short steps through the choices that
    shape the desktop most. Each applies as it's picked, and any can be skipped.
    It opens by itself the first time Tweaks starts; the Theme page (or
    --welcome) brings it back.
    SPDX-License-Identifier: GPL-3.0-or-later
*/
import QtQuick
import QtQuick.Controls as QQC2
import QtQuick.Layouts
import org.kde.kirigami as Kirigami
import "../controls"

Kirigami.ScrollablePage {
    id: page
    title: qsTr("Welcome")

    property int step: 0
    readonly property var steps: [qsTr("Look"), qsTr("Desktop"), qsTr("Dock"), qsTr("Control Center"),
                                  qsTr("Touchpad"), qsTr("Done")]
    readonly property int stepCount: steps.length
    readonly property bool last: step === stepCount - 1
    readonly property bool wide: width > Kirigami.Units.gridUnit * 36
    readonly property var pad: inputSettings.values
    property string pendingAccent: backend.accent
    property string pendingName: backend.paletteName

    function finish() {
        applicationWindow().showPage("theme");
    }

    Component.onCompleted: backend.setWelcomed()
    onStepChanged: if (page.flickable) {
        page.flickable.contentY = page.flickable.originY;
    }

    // the dock at the size picked, its middle icon swelling as under the pointer
    component DockPreview: Item {
        id: preview
        property real size: 48
        property real zoom: 1.7
        property real reach: 3
        readonly property var apps: ["org.kde.dolphin", "internet-web-browser", "org.kde.konsole", "org.kde.kwrite",
                                     "org.kde.discover", "systemsettings", "user-trash"]
        readonly property int middle: Math.floor(apps.length / 2)
        readonly property real gap: size * 0.14
        readonly property real shelf: apps.length * size + (apps.length + 1) * gap
        // shrunk to fit, never grown
        readonly property real fit: Math.min(1, width / (shelf + size * (zoom - 1) * 1.6))

        function swell(i) {
            const d = Math.abs(i - middle) / Math.max(0.5, reach);
            return 1 + (zoom - 1) * Math.max(0, Math.cos(Math.min(1, d) * Math.PI / 2));
        }

        implicitHeight: size * fit * (zoom + 0.4) + Kirigami.Units.largeSpacing

        Rectangle {
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.bottom: parent.bottom
            width: preview.shelf * preview.fit
            height: (preview.size + preview.gap * 2) * preview.fit
            radius: height * 0.32
            color: Qt.rgba(Kirigami.Theme.textColor.r, Kirigami.Theme.textColor.g, Kirigami.Theme.textColor.b, 0.07)
            border.width: 1
            border.color: Qt.rgba(Kirigami.Theme.textColor.r, Kirigami.Theme.textColor.g, Kirigami.Theme.textColor.b, 0.15)
        }
        Row {
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.bottom: parent.bottom
            anchors.bottomMargin: preview.gap * preview.fit
            spacing: preview.gap * preview.fit
            Repeater {
                model: preview.apps
                delegate: Kirigami.Icon {
                    required property string modelData
                    required property int index
                    readonly property real grown: preview.size * preview.fit * preview.swell(index)
                    anchors.bottom: parent.bottom
                    width: grown
                    height: grown
                    source: modelData
                    fallback: "application-x-executable"
                }
            }
        }
    }

    footer: QQC2.ToolBar {
        contentItem: RowLayout {
            spacing: Kirigami.Units.smallSpacing
            QQC2.Button {
                visible: !page.last
                flat: true
                text: qsTr("Skip the Tour")
                onClicked: page.finish()
            }
            Item {
                Layout.fillWidth: true
            }
            QQC2.Button {
                text: qsTr("Back")
                icon.name: "go-previous"
                enabled: page.step > 0
                onClicked: page.step -= 1
            }
            QQC2.Button {
                text: page.last ? qsTr("Finish") : qsTr("Next")
                icon.name: page.last ? "dialog-ok-apply" : "go-next"
                highlighted: true
                onClicked: {
                    if (page.last) {
                        page.finish();
                    } else {
                        page.step += 1;
                    }
                }
            }
        }
    }

    ColumnLayout {
        spacing: Kirigami.Units.largeSpacing

        Pills {
            id: pills
        }

        // where the tour is; each step can be jumped to
        Flow {
            Layout.fillWidth: true
            spacing: Kirigami.Units.smallSpacing

            Repeater {
                model: page.steps
                delegate: QQC2.AbstractButton {
                    id: marker
                    required property string modelData
                    required property int index
                    readonly property bool current: index === page.step
                    readonly property bool passed: index < page.step
                    padding: Kirigami.Units.smallSpacing
                    hoverEnabled: true
                    text: modelData
                    Accessible.name: qsTr("Step %1 of %2: %3").arg(index + 1).arg(page.stepCount).arg(modelData)
                    onClicked: page.step = index

                    background: Rectangle {
                        radius: height / 2
                        color: marker.hovered || marker.visualFocus
                            ? Qt.rgba(Kirigami.Theme.highlightColor.r, Kirigami.Theme.highlightColor.g,
                                      Kirigami.Theme.highlightColor.b, 0.12)
                            : "transparent"
                    }
                    contentItem: RowLayout {
                        spacing: Kirigami.Units.smallSpacing
                        Rectangle {
                            implicitWidth: Kirigami.Units.gridUnit * 1.3
                            implicitHeight: implicitWidth
                            radius: width / 2
                            color: marker.current || marker.passed ? Kirigami.Theme.highlightColor : "transparent"
                            border.width: marker.current || marker.passed ? 0 : 1
                            border.color: Qt.rgba(Kirigami.Theme.textColor.r, Kirigami.Theme.textColor.g,
                                                  Kirigami.Theme.textColor.b, 0.35)
                            QQC2.Label {
                                anchors.centerIn: parent
                                text: marker.passed ? "✓" : String(marker.index + 1)
                                color: marker.current || marker.passed ? Kirigami.Theme.highlightedTextColor
                                                                       : Kirigami.Theme.textColor
                                font: Kirigami.Theme.smallFont
                            }
                        }
                        QQC2.Label {
                            visible: page.wide || marker.current
                            text: marker.modelData
                            font.bold: marker.current
                            opacity: marker.current ? 1 : 0.7
                        }
                    }
                }
            }
        }

        Loader {
            Layout.fillWidth: true
            sourceComponent: [lookStep, desktopStep, dockStep, controlsStep, touchStep, doneStep][page.step]
        }
    }

    // ------------------------------------------------------------ 1. look --
    Component {
        id: lookStep
        ColumnLayout {
            spacing: Kirigami.Units.largeSpacing

            Kirigami.Heading {
                Layout.fillWidth: true
                level: 1
                wrapMode: Text.WordWrap
                text: qsTr("Welcome to Borealis")
            }
            QQC2.Label {
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
                text: qsTr("Six quick steps set up your desktop. What you pick shows straight away, and whatever you skip keeps the Borealis defaults. The Theme page brings this tour back any time.")
            }

            Kirigami.Heading {
                level: 3
                text: qsTr("Dark or light")
            }
            Flow {
                Layout.fillWidth: true
                spacing: Kirigami.Units.largeSpacing
                Repeater {
                    model: [["dark", qsTr("Dark"), qsTr("Deep ink blue, easy on the eyes")],
                            ["light", qsTr("Light"), qsTr("Bright frosted glass")],
                            ["auto", qsTr("Day and night"), qsTr("Light by day, dark after sunset")]]
                    delegate: PresetCard {
                        required property var modelData
                        width: Kirigami.Units.gridUnit * 10
                        text: modelData[1]
                        subtitle: modelData[2]
                        selected: backend.variant === modelData[0]
                        enabled: !backend.busy
                        summary: ({variant: modelData[0], accent: backend.accent, barFloating: true, clock: "center",
                                   dockSize: 48, dockZoom: 1.7, dockPosition: "bottom",
                                   buttons: ["minimize", "maximize", "close"]})
                        onClicked: if (backend.variant !== modelData[0]) {
                            backend.setVariant(modelData[0]);
                        }
                    }
                }
            }

            Kirigami.Heading {
                level: 3
                text: qsTr("Accent colour")
            }
            Flow {
                Layout.fillWidth: true
                spacing: Kirigami.Units.smallSpacing
                Repeater {
                    model: backend.presets
                    delegate: QQC2.AbstractButton {
                        id: swatch
                        required property var modelData
                        readonly property bool chosen: page.pendingAccent.toLowerCase() === modelData.color.toLowerCase()
                        implicitWidth: Kirigami.Units.gridUnit * 2.2
                        implicitHeight: implicitWidth
                        enabled: backend.hasProject && !backend.busy
                        hoverEnabled: true
                        text: modelData.name
                        QQC2.ToolTip.visible: hovered
                        QQC2.ToolTip.text: qsTr("%1: %2").arg(modelData.name).arg(modelData.hint)
                        onClicked: {
                            page.pendingAccent = modelData.color;
                            page.pendingName = modelData.name === "Nocturne" ? "Borealis" : "Borealis " + modelData.name;
                        }
                        contentItem: Item {}
                        background: Rectangle {
                            radius: width / 2
                            color: swatch.modelData.color
                            opacity: swatch.enabled ? 1 : 0.5
                            border.width: swatch.chosen ? 3 : 1
                            border.color: swatch.chosen ? Kirigami.Theme.textColor
                                : Qt.rgba(Kirigami.Theme.textColor.r, Kirigami.Theme.textColor.g,
                                          Kirigami.Theme.textColor.b, 0.3)
                        }
                    }
                }
            }
            Kirigami.InlineMessage {
                Layout.fillWidth: true
                visible: page.pendingAccent.toLowerCase() !== backend.accent.toLowerCase()
                type: Kirigami.MessageType.Information
                text: qsTr("Borealis is rebuilt around %1, which takes about half a minute; your other settings stay as they are.")
                          .arg(page.pendingName)
                actions: [
                    Kirigami.Action {
                        text: qsTr("Rebuild")
                        icon.name: "dialog-ok-apply"
                        enabled: backend.hasProject && !backend.busy
                        onTriggered: backend.remix(page.pendingAccent, page.pendingName, backend.gtkColors,
                                                   backend.terminalKit)
                    },
                    Kirigami.Action {
                        text: qsTr("Keep %1").arg(backend.paletteName)
                        onTriggered: {
                            page.pendingAccent = backend.accent;
                            page.pendingName = backend.paletteName;
                        }
                    }
                ]
            }
            Hint {
                visible: !backend.hasProject
                text: qsTr("New colours need the Borealis project folder, which wasn't found.")
            }

            QQC2.Switch {
                Layout.fillWidth: true
                text: qsTr("Animated aurora on the desktop and lock screen")
                enabled: !backend.busy
                checked: backend.liveWallpaper
                onToggled: {
                    backend.setLiveWallpaper(checked);
                    checked = Qt.binding(() => backend.liveWallpaper);
                }
            }

            JobLog {}
        }
    }

    // --------------------------------------------------------- 2. desktop --
    Component {
        id: desktopStep
        ColumnLayout {
            spacing: Kirigami.Units.largeSpacing

            Kirigami.Heading {
                Layout.fillWidth: true
                level: 2
                wrapMode: Text.WordWrap
                text: qsTr("Pick a desktop")
            }
            QQC2.Label {
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
                text: qsTr("Each one sets the dock, the bar and its Control Center, the title bar and the hot corners together. Pick one to try it on your desktop, and another if you'd rather.")
            }
            Kirigami.InlineMessage {
                Layout.fillWidth: true
                visible: presetsSettings.canUndo && presetsSettings.lastApplied !== ""
                type: Kirigami.MessageType.Positive
                text: qsTr("%1 is on.").arg(presetsSettings.lastApplied)
                actions: [
                    Kirigami.Action {
                        text: qsTr("Undo")
                        icon.name: "edit-undo"
                        enabled: !backend.busy
                        onTriggered: presetsSettings.undo()
                    }
                ]
            }
            Flow {
                Layout.fillWidth: true
                spacing: Kirigami.Units.largeSpacing
                Repeater {
                    model: presetsSettings.presets.filter(preset => preset.builtin)
                    delegate: PresetCard {
                        required property var modelData
                        width: Kirigami.Units.gridUnit * 12
                        text: modelData.name
                        subtitle: modelData.current ? qsTr("In use") : modelData.description
                        summary: modelData.thumb
                        selected: modelData.current
                        enabled: !backend.busy
                        onClicked: if (!modelData.current) {
                            presetsSettings.apply(modelData.id, modelData.sections, false);
                        }
                    }
                }
            }
            Hint {
                text: qsTr("The Presets page has these too, beside your own: save this desktop as a preset, or share it as a file.")
            }
        }
    }

    // ------------------------------------------------------------ 3. dock --
    Component {
        id: dockStep
        ColumnLayout {
            spacing: Kirigami.Units.largeSpacing

            Kirigami.Heading {
                Layout.fillWidth: true
                level: 2
                wrapMode: Text.WordWrap
                text: qsTr("Size up the dock")
            }
            QQC2.Label {
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
                text: qsTr("How big its icons are, and how much they swell as the pointer passes over them.")
            }
            Kirigami.InlineMessage {
                Layout.fillWidth: true
                visible: !dockSettings.installed
                type: Kirigami.MessageType.Information
                text: qsTr("You're using the panel dock. These settings are for the standalone Borealis Dock, which magnifies without a ceiling.")
                actions: [
                    Kirigami.Action {
                        text: qsTr("Switch to it")
                        icon.name: "dialog-ok-apply"
                        enabled: dockSettings.canSwitch && !backend.busy
                        onTriggered: dockSettings.enable()
                    }
                ]
            }
            DockPreview {
                Layout.fillWidth: true
                size: Number(dockSettings.values.iconSize) || 48
                zoom: Number(dockSettings.values.zoom) || 1
                reach: Number(dockSettings.values.reach) || 3
            }
            Kirigami.FormLayout {
                Layout.fillWidth: true
                Amount {
                    Kirigami.FormData.label: qsTr("Icons:")
                    target: dockSettings
                    key: "iconSize"
                    from: 24
                    to: 128
                    stepSize: 2
                    describe: value => qsTr("%1 px").arg(Math.round(value))
                }
                Amount {
                    Kirigami.FormData.label: qsTr("Magnification:")
                    target: dockSettings
                    key: "zoom"
                    from: 1
                    to: 3
                    stepSize: 0.05
                    describe: value => value <= 1.001 ? qsTr("Off") : qsTr("%1×").arg(value.toFixed(2))
                }
                Choice {
                    Kirigami.FormData.label: qsTr("Screen edge:")
                    target: dockSettings
                    key: "position"
                    choices: [["bottom", qsTr("Bottom")], ["left", qsTr("Left")], ["right", qsTr("Right")]]
                }
                Choice {
                    Kirigami.FormData.label: qsTr("Hiding:")
                    target: dockSettings
                    key: "hide"
                    choices: [["always", qsTr("Always visible")], ["dodge", qsTr("Hide when a window covers it")],
                              ["auto", qsTr("Hide when not in use")]]
                }
            }
        }
    }

    // ------------------------------------------------- 4. control center --
    Component {
        id: controlsStep
        ColumnLayout {
            spacing: Kirigami.Units.largeSpacing
            readonly property int chosenCount: (barSettings.values.pills || []).length

            Kirigami.Heading {
                Layout.fillWidth: true
                level: 2
                wrapMode: Text.WordWrap
                text: qsTr("Choose your toggles")
            }
            QQC2.Label {
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
                text: qsTr("The Control Center, at the right of the bar, opens with round buttons for what you change most. Pick the ones you want; its pencil button puts them in order later.")
            }
            Kirigami.InlineMessage {
                Layout.fillWidth: true
                visible: !barSettings.installed
                type: Kirigami.MessageType.Information
                text: qsTr("The Control Center comes with the Borealis Bar, which isn't on. What you pick here waits for it.")
                actions: [
                    Kirigami.Action {
                        text: qsTr("Switch to the bar")
                        icon.name: "dialog-ok-apply"
                        enabled: barSettings.canSwitch && !backend.busy
                        onTriggered: barSettings.enable()
                    }
                ]
            }
            Flow {
                Layout.fillWidth: true
                spacing: Kirigami.Units.smallSpacing
                Repeater {
                    model: barSettings.pills
                    delegate: QQC2.Button {
                        required property string modelData
                        readonly property bool chosen: (barSettings.values.pills || []).indexOf(modelData) >= 0
                        checkable: true
                        checked: chosen
                        text: pills.names[modelData]
                        icon.name: pills.icons[modelData]
                        QQC2.ToolTip.text: pills.hints[modelData]
                        QQC2.ToolTip.visible: hovered
                        QQC2.ToolTip.delay: Kirigami.Units.toolTipDelay
                        onToggled: {
                            barSettings.setPill(modelData, checked);
                            checked = Qt.binding(() => chosen);
                        }
                    }
                }
            }
            Hint {
                text: (chosenCount === 1 ? qsTr("1 toggle chosen.") : qsTr("%1 toggles chosen.").arg(chosenCount))
                      + " " + qsTr("One this computer has no use for, like Keyboard Light without a lit keyboard, stays out of sight.")
            }
        }
    }

    // -------------------------------------------------------- 5. touchpad --
    Component {
        id: touchStep
        ColumnLayout {
            spacing: Kirigami.Units.largeSpacing

            Kirigami.Heading {
                Layout.fillWidth: true
                level: 2
                wrapMode: Text.WordWrap
                text: qsTr("Touchpad and keys")
            }
            QQC2.Label {
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
                text: qsTr("How the touchpad clicks and scrolls, and whether a tap of Meta opens Launchpad.")
            }
            Kirigami.InlineMessage {
                Layout.fillWidth: true
                visible: (page.pad.touchpad || "") === ""
                type: Kirigami.MessageType.Information
                text: qsTr("No touchpad was found, so there's just the Meta key here.")
            }
            Kirigami.FormLayout {
                Layout.fillWidth: true
                Toggle {
                    Kirigami.FormData.label: qsTr("Tap to click:")
                    visible: page.pad.canTap === true
                    target: inputSettings
                    key: "tapToClick"
                }
                Choice {
                    Kirigami.FormData.label: qsTr("Right-click by pressing:")
                    visible: page.pad.canRightClick === true
                    target: inputSettings
                    key: "rightClick"
                    choices: [["corner", qsTr("The bottom-right corner")], ["twoFingers", qsTr("With two fingers")]]
                }
                Hint {
                    visible: page.pad.canRightClick === true
                    text: page.pad.rightClick === "corner"
                        ? qsTr("A press with two fingers anywhere else is a left click.")
                        : qsTr("Pressing anywhere with two fingers right-clicks, and with three middle-clicks.")
                }
                Toggle {
                    Kirigami.FormData.label: qsTr("Natural scrolling:")
                    visible: page.pad.can_naturalScroll === true
                    target: inputSettings
                    key: "naturalScroll"
                }
                Hint {
                    visible: page.pad.can_naturalScroll === true
                    text: qsTr("The page follows your fingers, as on a phone.")
                }

                Kirigami.Separator {
                    Kirigami.FormData.isSection: true
                    Kirigami.FormData.label: qsTr("Launchpad")
                }
                Toggle {
                    Kirigami.FormData.label: qsTr("A tap of Meta opens it:")
                    visible: page.pad.hasLaunchpad === true
                    target: inputSettings
                    key: "launchpadMeta"
                }
                QQC2.Label {
                    Kirigami.FormData.label: qsTr("Its keys:")
                    visible: page.pad.hasLaunchpad === true && dockSettings.launchpadKey !== ""
                    text: dockSettings.launchpadKey
                    opacity: 0.8
                }
                Hint {
                    visible: page.pad.hasLaunchpad !== true
                    text: qsTr("Launchpad comes with the Borealis Dock: every app and a search, over the whole screen.")
                }
            }
        }
    }

    // ------------------------------------------------------------ 6. done --
    Component {
        id: doneStep
        ColumnLayout {
            spacing: Kirigami.Units.largeSpacing

            Kirigami.Heading {
                Layout.fillWidth: true
                level: 2
                wrapMode: Text.WordWrap
                text: qsTr("You're all set")
            }
            QQC2.Label {
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
                text: qsTr("Here's where things live.")
            }
            Kirigami.InlineMessage {
                Layout.fillWidth: true
                visible: !barSettings.installed
                type: Kirigami.MessageType.Information
                text: qsTr("The menu, the clock and the Control Center are part of the Borealis Bar, which isn't on yet.")
                actions: [
                    Kirigami.Action {
                        text: qsTr("Switch to the bar")
                        icon.name: "dialog-ok-apply"
                        enabled: barSettings.canSwitch && !backend.busy
                        onTriggered: barSettings.enable()
                    }
                ]
            }
            GridLayout {
                Layout.fillWidth: true
                columns: page.wide ? 2 : 1
                columnSpacing: Kirigami.Units.largeSpacing * 2
                rowSpacing: Kirigami.Units.largeSpacing

                Repeater {
                    model: [
                        ["borealis", qsTr("The Borealis menu"),
                         qsTr("At the left of the bar: About this computer, System Settings, Borealis Tweaks, Force Quit, sleep and power.")],
                        ["office-calendar", qsTr("The clock"), qsTr("Your notifications, Do Not Disturb and the calendar.")],
                        ["adjustlevels", qsTr("The Control Center"),
                         qsTr("At the right of the bar: Wi-Fi, Bluetooth, sound and your toggles. Its pencil button rearranges them.")],
                        ["view-grid", qsTr("Launchpad"), dockSettings.launchpadKey !== ""
                            ? qsTr("Every app and a search, on %1.").arg(dockSettings.launchpadKey)
                            : qsTr("Every app and a search, from its icon in the dock.")],
                        ["preferences-desktop-display", qsTr("The dock"),
                         qsTr("Drag icons along it to reorder them, or off it to remove them. Right-click the shelf for its presets.")],
                        ["preferences-desktop-theme-global", qsTr("Borealis Tweaks"),
                         qsTr("In the Borealis menu: everything from this tour and much more, with presets for the whole desktop.")]
                    ]
                    delegate: RowLayout {
                        required property var modelData
                        Layout.fillWidth: true
                        Layout.preferredWidth: Kirigami.Units.gridUnit * 14
                        Layout.alignment: Qt.AlignTop
                        spacing: Kirigami.Units.largeSpacing

                        Kirigami.Icon {
                            Layout.alignment: Qt.AlignTop
                            Layout.preferredWidth: Kirigami.Units.iconSizes.medium
                            Layout.preferredHeight: Kirigami.Units.iconSizes.medium
                            source: modelData[0]
                        }
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 0
                            QQC2.Label {
                                Layout.fillWidth: true
                                text: modelData[1]
                                font.bold: true
                                wrapMode: Text.WordWrap
                            }
                            QQC2.Label {
                                Layout.fillWidth: true
                                Layout.minimumWidth: Kirigami.Units.gridUnit * 8
                                text: modelData[2]
                                wrapMode: Text.WordWrap
                                opacity: 0.8
                            }
                        }
                    }
                }
            }
            Flow {
                Layout.fillWidth: true
                spacing: Kirigami.Units.smallSpacing
                QQC2.Button {
                    text: qsTr("Browse Presets")
                    icon.name: "bookmarks"
                    onClicked: applicationWindow().showPage("presets")
                }
            }
        }
    }
}
