/*
    The quick settings' plumbing: one probe command reads every value at once,
    each toggle is a single command. Nothing here needs a private Plasma API,
    so a missing tool only makes its own tile disappear.
    SPDX-License-Identifier: GPL-3.0-or-later
*/

import QtQuick
import org.kde.plasma.plasma5support as P5Support

QtObject {
    id: backend

    property bool active: false          // only poll while the popup is open
    property var state: ({})
    signal refreshed()

    readonly property string probeScript: [
        'printf "wifi=%s\\n" "$(nmcli -t radio wifi 2>/dev/null)"',
        'printf "bt=%s\\n" "$(bluetoothctl show 2>/dev/null | awk \'/Powered:/ {print $2; exit}\')"',
        'printf "night=%s\\n" "$(qdbus-qt6 org.kde.KWin /org/kde/KWin/NightLight org.kde.KWin.NightLight.enabled 2>/dev/null)"',
        'printf "profile=%s\\n" "$(busctl --system get-property net.hadess.PowerProfiles /net/hadess/PowerProfiles net.hadess.PowerProfiles ActiveProfile 2>/dev/null | cut -d\\" -f2)"',
        'printf "bright=%s\\n" "$(qdbus-qt6 org.kde.Solid.PowerManagement /org/kde/Solid/PowerManagement/Actions/BrightnessControl org.kde.Solid.PowerManagement.Actions.BrightnessControl.brightness 2>/dev/null)"',
        'printf "brightmax=%s\\n" "$(qdbus-qt6 org.kde.Solid.PowerManagement /org/kde/Solid/PowerManagement/Actions/BrightnessControl org.kde.Solid.PowerManagement.Actions.BrightnessControl.brightnessMax 2>/dev/null)"',
        'printf "volume=%s\\n" "$(wpctl get-volume @DEFAULT_AUDIO_SINK@ 2>/dev/null)"',
        'printf "theme=%s\\n" "$(kreadconfig6 --file kdeglobals --group KDE --key LookAndFeelPackage 2>/dev/null)"',
        'printf "wallpaper=%s\\n" "$(qdbus-qt6 org.kde.plasmashell /PlasmaShell org.kde.PlasmaShell.evaluateScript \'var d = desktops(); print(d[0].wallpaperPlugin);\' 2>/dev/null)"',
    ].join("; ")

    function refresh() {
        source.connectSource(probeScript);
    }

    function run(command) {
        source.connectSource(command);
        // give the change a moment to land, then read everything back
        settle.restart();
    }

    property Timer settle: Timer {
        interval: 700
        onTriggered: backend.refresh()
    }

    property Timer poll: Timer {
        interval: 5000
        repeat: true
        running: backend.active
        triggeredOnStart: true
        onTriggered: backend.refresh()
    }

    property P5Support.DataSource source: P5Support.DataSource {
        engine: "executable"
        connectedSources: []
        onNewData: (sourceName, data) => {
            disconnectSource(sourceName);
            const text = (data["stdout"] || "").toString();
            if (!text.includes("=")) {
                return;
            }
            const next = {};
            for (const line of text.split("\n")) {
                const at = line.indexOf("=");
                if (at > 0) {
                    next[line.slice(0, at)] = line.slice(at + 1).trim();
                }
            }
            backend.state = next;
            backend.refreshed();
        }
    }

    // ------------------------------------------------------------ values --
    readonly property bool wifiAvailable: state.wifi === "enabled" || state.wifi === "disabled"
    readonly property bool wifiOn: state.wifi === "enabled"
    readonly property bool btAvailable: state.bt === "yes" || state.bt === "no"
    readonly property bool btOn: state.bt === "yes"
    readonly property bool nightAvailable: state.night === "true" || state.night === "false"
    readonly property bool nightOn: state.night === "true"
    readonly property string profile: state.profile || ""
    readonly property bool profileAvailable: profile.length > 0
    readonly property int brightness: parseInt(state.bright || "0")
    readonly property int brightnessMax: parseInt(state.brightmax || "0")
    readonly property bool brightnessAvailable: brightnessMax > 0
    // "Volume: 0.55" or "Volume: 0.55 [MUTED]"
    readonly property real volume: {
        const m = /Volume:\s*([0-9.]+)/.exec(state.volume || "");
        return m ? parseFloat(m[1]) : -1;
    }
    readonly property bool volumeAvailable: volume >= 0
    readonly property bool muted: (state.volume || "").includes("MUTED")
    readonly property string lookAndFeel: state.theme || ""
    readonly property bool isLight: lookAndFeel.endsWith("-Light")
    readonly property string wallpaperPlugin: state.wallpaper || ""
    readonly property bool auroraOn: wallpaperPlugin.endsWith(".aurora")

    // ----------------------------------------------------------- actions --
    function toggleWifi() {
        run("nmcli radio wifi " + (wifiOn ? "off" : "on"));
    }
    function toggleBluetooth() {
        run("bluetoothctl power " + (btOn ? "off" : "on"));
    }
    function toggleNight() {
        run("kwriteconfig6 --file kwinrc --group NightColor --key Active " + (nightOn ? "false" : "true")
            + "; qdbus-qt6 org.kde.KWin /KWin org.kde.KWin.reconfigure");
    }
    function cycleProfile() {
        const order = ["power-saver", "balanced", "performance"];
        const next = order[(Math.max(0, order.indexOf(profile)) + 1) % order.length];
        run("busctl --system set-property net.hadess.PowerProfiles /net/hadess/PowerProfiles"
            + " net.hadess.PowerProfiles ActiveProfile s " + next);
    }
    function setBrightness(value) {
        run("qdbus-qt6 org.kde.Solid.PowerManagement /org/kde/Solid/PowerManagement/Actions/BrightnessControl"
            + " org.kde.Solid.PowerManagement.Actions.BrightnessControl.setBrightness "
            + Math.round(value));
    }
    function setVolume(fraction) {
        run("wpctl set-volume @DEFAULT_AUDIO_SINK@ " + Math.round(fraction * 100) + "%");
    }
    function toggleMute() {
        run("wpctl set-mute @DEFAULT_AUDIO_SINK@ toggle");
    }
    function toggleTheme(darkPkg, lightPkg) {
        run("plasma-apply-lookandfeel -a " + (isLight ? darkPkg : lightPkg));
    }
    function toggleAurora(auroraPlugin) {
        const plugin = auroraOn ? "org.kde.image" : auroraPlugin;
        run("qdbus-qt6 org.kde.plasmashell /PlasmaShell org.kde.PlasmaShell.evaluateScript "
            + "\"var d = desktops(); for (var i = 0; i < d.length; i++) { d[i].wallpaperPlugin = '"
            + plugin + "'; }\"");
    }
    function openSettings(module) {
        run("systemsettings " + module);
    }
    function lockScreen() {
        run("qdbus-qt6 org.kde.screensaver /ScreenSaver org.freedesktop.ScreenSaver.Lock");
    }
}
