/*
    Borealis Aurora — animated wallpaper for the desktop and the lock screen.
    SPDX-License-Identifier: GPL-3.0-or-later
*/

import QtQuick
import org.kde.kirigami as Kirigami
import org.kde.plasma.plasmoid

WallpaperItem {
    id: root

    readonly property bool schemeIsDark: {
        const c = Kirigami.Theme.backgroundColor;
        return (0.2126 * c.r + 0.7152 * c.g + 0.0722 * c.b) < 0.5;
    }
    readonly property int variant: root.configuration.Variant
    readonly property bool night: variant === 1 || (variant === 0 && schemeIsDark)

    // the lock screen sets this context property; plasmashell doesn't
    readonly property bool onLockScreen: typeof kscreenlocker_userName !== "undefined"
    // after a greeter crash the lock screen runs without a GPU: shaders draw nothing
    readonly property bool software: GraphicsInfo.api === GraphicsInfo.Software

    readonly property bool reducedMotion: Kirigami.Units.longDuration <= 1
    readonly property bool covered: pauseLoader.item ? pauseLoader.item.covered : false
    readonly property bool onBattery: powerLoader.item ? powerLoader.item.onBattery : false
    readonly property bool animating: visible && !software && !reducedMotion
        && !(root.configuration.PauseWhenCovered && covered)
        && !(root.configuration.PauseOnBattery && onBattery)
    // the lock screen blurs every frame again; keep it cheaper there
    readonly property int fps: Math.max(5, Math.min(onLockScreen ? 15 : 60, root.configuration.Fps))

    // "accent color from wallpaper" would otherwise sample a random frame
    accentColor: night ? "#8b9cff" : "#5566e0"

    // Animation clock. Shaders work in 32-bit floats, so the clock wraps before
    // the noise loses precision; the last seconds before the wrap crossfade to
    // a second aurora that already runs on the restarted clock, so the jump
    // never shows.
    readonly property real wrapAt: 1800
    readonly property real fade: 8
    property real t: Math.random() * 600
    readonly property real restartT: t - (wrapAt - fade)
    readonly property real handover: Math.max(0, Math.min(1, restartT / fade))

    Timer {
        interval: Math.round(1000 / root.fps)
        repeat: true
        running: root.animating
        onTriggered: {
            let next = root.t + interval / 1000 * root.configuration.Speed;
            if (next >= root.wrapAt) {
                next -= root.wrapAt - root.fade;
            }
            root.t = next;
        }
    }

    Rectangle {
        anchors.fill: parent
        color: root.night ? "#070a12" : "#b7c3f5"
    }

    Image {
        id: sky
        anchors.fill: parent
        source: root.night ? "../images/sky-night.jpg" : "../images/sky-dawn.jpg"
        fillMode: Image.PreserveAspectCrop
        clip: true
        smooth: true
        layer.enabled: !root.software
        // drawn through the twinkle shader, or directly without a GPU
        visible: root.software
    }

    ShaderEffect {
        anchors.fill: parent
        visible: !root.software
        property variant source: sky
        property real time: root.t
        property real amount: root.night && root.configuration.Twinkle ? 0.6 : 0.0
        property size cells: Qt.size(width / 4, height / 4)
        fragmentShader: Qt.resolvedUrl("../shaders/twinkle.frag.qsb")
    }

    component Aurora: ShaderEffect {
        anchors.fill: parent
        property real time
        property real intensity: root.configuration.Intensity / 100
        property real dawn: root.night ? 0.0 : 1.0
        fragmentShader: Qt.resolvedUrl("../shaders/aurora.frag.qsb")
        // the aurora is soft; rendering it at half size keeps the GPU cool
        layer.enabled: true
        layer.smooth: true
        layer.textureSize: Qt.size(Math.max(1, Math.round(width / 2)), Math.max(1, Math.round(height / 2)))
    }

    Aurora {
        time: root.t
        opacity: 1 - root.handover
        visible: !root.software && opacity > 0
    }

    Aurora {
        time: root.restartT
        opacity: root.handover
        visible: !root.software && opacity > 0
    }

    Image {
        anchors.fill: parent
        source: root.night ? "../images/mountains-night.png" : "../images/mountains-dawn.png"
        fillMode: Image.PreserveAspectCrop
        smooth: true
    }

    // Optional helpers: loaded separately so a missing module can never break
    // the wallpaper itself. Windows behind the lock screen don't matter.
    Loader {
        id: pauseLoader
        active: root.configuration.PauseWhenCovered && !root.onLockScreen
        source: "PauseDetector.qml"
    }
    Loader {
        id: powerLoader
        active: root.configuration.PauseOnBattery
        source: "PowerState.qml"
    }
}
