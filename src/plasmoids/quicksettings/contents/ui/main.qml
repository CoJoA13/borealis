/*
    Borealis Quick Settings — the toggles you reach for most, in one frosted
    popup: radios, night light, power profile, the theme's own light/dark and
    animated wallpaper, plus brightness and volume.
    SPDX-License-Identifier: GPL-3.0-or-later
*/

import QtQuick
import QtQuick.Layouts
import org.kde.kirigami as Kirigami
import org.kde.plasma.components as PlasmaComponents3
import org.kde.plasma.core as PlasmaCore
import org.kde.plasma.extras as PlasmaExtras
import org.kde.plasma.plasmoid

PlasmoidItem {
    id: root

    readonly property string darkPackage: Plasmoid.configuration.darkPackage
    readonly property string lightPackage: Plasmoid.configuration.lightPackage
    readonly property string auroraPlugin: Plasmoid.configuration.auroraPlugin

    Plasmoid.icon: "configure"
    toolTipMainText: i18nd("plasma_applet_org.borealis.quicksettings", "Quick Settings")
    toolTipSubText: i18nd("plasma_applet_org.borealis.quicksettings",
                          "Radios, night light, power, brightness and volume")
    // a panel gets the icon, the desktop or a window gets the whole popup
    preferredRepresentation: Plasmoid.formFactor === PlasmaCore.Types.Planar
        ? fullRepresentation : compactRepresentation

    Backend {
        id: backend
        active: root.expanded
    }

    compactRepresentation: MouseArea {
        onClicked: root.expanded = !root.expanded
        Kirigami.Icon {
            anchors.fill: parent
            anchors.margins: Kirigami.Units.smallSpacing / 2
            source: "configure"
            active: parent.containsMouse
        }
        hoverEnabled: true
    }

    fullRepresentation: PlasmaExtras.Representation {
        Layout.minimumWidth: Kirigami.Units.gridUnit * 20
        Layout.minimumHeight: Kirigami.Units.gridUnit * 24
        Layout.preferredWidth: Kirigami.Units.gridUnit * 20
        Layout.preferredHeight: Kirigami.Units.gridUnit * 24

        header: PlasmaExtras.PlasmoidHeading {
            RowLayout {
                anchors.fill: parent
                PlasmaExtras.Heading {
                    level: 4
                    text: i18nd("plasma_applet_org.borealis.quicksettings", "Quick Settings")
                    Layout.fillWidth: true
                }
                PlasmaComponents3.ToolButton {
                    icon.name: "system-lock-screen"
                    display: PlasmaComponents3.AbstractButton.IconOnly
                    text: i18nd("plasma_applet_org.borealis.quicksettings", "Lock screen")
                    PlasmaComponents3.ToolTip.text: text
                    PlasmaComponents3.ToolTip.visible: hovered
                    onClicked: backend.lockScreen()
                }
                PlasmaComponents3.ToolButton {
                    icon.name: "configure"
                    display: PlasmaComponents3.AbstractButton.IconOnly
                    text: i18nd("plasma_applet_org.borealis.quicksettings", "All settings…")
                    PlasmaComponents3.ToolTip.text: text
                    PlasmaComponents3.ToolTip.visible: hovered
                    onClicked: {
                        backend.openSettings("");
                        root.expanded = false;
                    }
                }
            }
        }

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: Kirigami.Units.smallSpacing
            spacing: Kirigami.Units.smallSpacing

            GridLayout {
                Layout.fillWidth: true
                columns: 2
                rowSpacing: Kirigami.Units.smallSpacing
                columnSpacing: Kirigami.Units.smallSpacing

                Tile {
                    label: i18nd("plasma_applet_org.borealis.quicksettings", "Wi-Fi")
                    sub: backend.wifiOn ? i18nd("plasma_applet_org.borealis.quicksettings", "On")
                                        : i18nd("plasma_applet_org.borealis.quicksettings", "Off")
                    iconName: backend.wifiOn ? "network-wireless-connected" : "network-wireless-disconnected"
                    active: backend.wifiOn
                    available: backend.wifiAvailable
                    onToggled: backend.toggleWifi()
                }

                Tile {
                    label: i18nd("plasma_applet_org.borealis.quicksettings", "Bluetooth")
                    sub: backend.btOn ? i18nd("plasma_applet_org.borealis.quicksettings", "On")
                                      : i18nd("plasma_applet_org.borealis.quicksettings", "Off")
                    iconName: backend.btOn ? "network-bluetooth" : "network-bluetooth-inactive"
                    active: backend.btOn
                    available: backend.btAvailable
                    onToggled: backend.toggleBluetooth()
                }

                Tile {
                    label: i18nd("plasma_applet_org.borealis.quicksettings", "Night Light")
                    sub: backend.nightOn ? i18nd("plasma_applet_org.borealis.quicksettings", "Warm")
                                         : i18nd("plasma_applet_org.borealis.quicksettings", "Off")
                    iconName: "redshift-status-on"
                    active: backend.nightOn
                    available: backend.nightAvailable
                    onToggled: backend.toggleNight()
                }

                Tile {
                    label: i18nd("plasma_applet_org.borealis.quicksettings", "Power")
                    sub: backend.profile === "power-saver"
                        ? i18nd("plasma_applet_org.borealis.quicksettings", "Power saver")
                        : backend.profile === "performance"
                        ? i18nd("plasma_applet_org.borealis.quicksettings", "Performance")
                        : i18nd("plasma_applet_org.borealis.quicksettings", "Balanced")
                    iconName: backend.profile === "performance" ? "speedometer"
                            : backend.profile === "power-saver" ? "battery-profile-powersave" : "battery"
                    active: backend.profile === "performance"
                    available: backend.profileAvailable
                    onToggled: backend.cycleProfile()
                }

                Tile {
                    label: i18nd("plasma_applet_org.borealis.quicksettings", "Theme")
                    sub: backend.isLight ? i18nd("plasma_applet_org.borealis.quicksettings", "Light")
                                         : i18nd("plasma_applet_org.borealis.quicksettings", "Dark")
                    iconName: backend.isLight ? "weather-clear" : "weather-clear-night"
                    active: !backend.isLight
                    available: backend.lookAndFeel.length > 0
                    onToggled: backend.toggleTheme(root.darkPackage, root.lightPackage)
                }

                Tile {
                    label: i18nd("plasma_applet_org.borealis.quicksettings", "Aurora")
                    sub: backend.auroraOn ? i18nd("plasma_applet_org.borealis.quicksettings", "Animated")
                                          : i18nd("plasma_applet_org.borealis.quicksettings", "Still")
                    iconName: "preferences-desktop-wallpaper"
                    active: backend.auroraOn
                    available: backend.wallpaperPlugin.length > 0
                    onToggled: backend.toggleAurora(root.auroraPlugin)
                }
            }

            Kirigami.Separator { Layout.fillWidth: true }

            // ------------------------------------------------------ sliders --
            RowLayout {
                Layout.fillWidth: true
                visible: backend.brightnessAvailable
                Kirigami.Icon {
                    source: "brightness-high"
                    isMask: true
                    Layout.preferredWidth: Kirigami.Units.iconSizes.smallMedium
                    Layout.preferredHeight: Kirigami.Units.iconSizes.smallMedium
                }
                PlasmaComponents3.Slider {
                    id: brightnessSlider
                    Layout.fillWidth: true
                    from: Math.max(1, backend.brightnessMax * 0.02)
                    to: Math.max(2, backend.brightnessMax)
                    value: backend.brightness
                    onMoved: backend.setBrightness(value)
                }
                PlasmaComponents3.Label {
                    text: backend.brightnessMax > 0
                        ? Math.round(brightnessSlider.value / backend.brightnessMax * 100) + "%" : ""
                    Layout.minimumWidth: Kirigami.Units.gridUnit * 2
                    horizontalAlignment: Text.AlignRight
                }
            }

            RowLayout {
                Layout.fillWidth: true
                visible: backend.volumeAvailable
                PlasmaComponents3.ToolButton {
                    icon.name: backend.muted ? "audio-volume-muted" : "audio-volume-high"
                    display: PlasmaComponents3.AbstractButton.IconOnly
                    text: i18nd("plasma_applet_org.borealis.quicksettings", "Mute")
                    onClicked: backend.toggleMute()
                }
                PlasmaComponents3.Slider {
                    id: volumeSlider
                    Layout.fillWidth: true
                    from: 0
                    to: 1
                    value: backend.volume
                    opacity: backend.muted ? 0.5 : 1
                    onMoved: backend.setVolume(value)
                }
                PlasmaComponents3.Label {
                    text: Math.round(volumeSlider.value * 100) + "%"
                    Layout.minimumWidth: Kirigami.Units.gridUnit * 2
                    horizontalAlignment: Text.AlignRight
                }
            }

            Item { Layout.fillHeight: true }
        }
    }
}
