/*
    Borealis Aurora settings page.
    SPDX-License-Identifier: GPL-3.0-or-later
*/

import QtQuick
import QtQuick.Controls as QQC2
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

Kirigami.FormLayout {
    id: root
    twinFormLayouts: parentLayout

    property alias formLayout: root
    property int cfg_Variant
    property alias cfg_Speed: speed.value
    property alias cfg_Intensity: intensity.value
    property alias cfg_Twinkle: twinkle.checked
    property alias cfg_Fps: fps.value
    property alias cfg_PauseWhenCovered: covered.checked
    property alias cfg_PauseOnBattery: battery.checked

    QQC2.ComboBox {
        Kirigami.FormData.label: i18nd("plasma_wallpaper_org.borealis.aurora", "Sky:")
        model: [i18nd("plasma_wallpaper_org.borealis.aurora", "Follow color scheme"), i18nd("plasma_wallpaper_org.borealis.aurora", "Always night"), i18nd("plasma_wallpaper_org.borealis.aurora", "Always dawn")]
        currentIndex: root.cfg_Variant
        onActivated: index => root.cfg_Variant = index
    }

    RowLayout {
        Kirigami.FormData.label: i18nd("plasma_wallpaper_org.borealis.aurora", "Speed:")
        QQC2.Slider {
            id: speed
            from: 0.25
            to: 3.0
            Layout.preferredWidth: Kirigami.Units.gridUnit * 12
        }
        QQC2.Label { text: speed.value.toFixed(2) + "×" }
    }

    RowLayout {
        Kirigami.FormData.label: i18nd("plasma_wallpaper_org.borealis.aurora", "Brightness:")
        QQC2.Slider {
            id: intensity
            from: 20
            to: 200
            Layout.preferredWidth: Kirigami.Units.gridUnit * 12
        }
        QQC2.Label { text: Math.round(intensity.value) + "%" }
    }

    QQC2.CheckBox {
        id: twinkle
        Kirigami.FormData.label: i18nd("plasma_wallpaper_org.borealis.aurora", "Stars:")
        text: i18nd("plasma_wallpaper_org.borealis.aurora", "Twinkle")
    }

    QQC2.SpinBox {
        id: fps
        Kirigami.FormData.label: i18nd("plasma_wallpaper_org.borealis.aurora", "Frame rate:")
        from: 10
        to: 60
    }

    QQC2.CheckBox {
        id: covered
        Kirigami.FormData.label: i18nd("plasma_wallpaper_org.borealis.aurora", "Save power:")
        text: i18nd("plasma_wallpaper_org.borealis.aurora", "Pause behind maximized or fullscreen windows")
    }

    QQC2.CheckBox {
        id: battery
        text: i18nd("plasma_wallpaper_org.borealis.aurora", "Pause on battery")
    }
}
