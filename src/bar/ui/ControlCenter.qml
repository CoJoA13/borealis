/*
    The Control Center: battery and session buttons, brightness and volume,
    the toggles (in the order the settings give), and what's playing.
    SPDX-License-Identifier: GPL-3.0-or-later
*/
import QtQuick
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

Card {
    id: center

    property var status: null
    property var notices: null
    signal dismissed()

    readonly property var cfg: bar.settings.values
    readonly property var profileNames: ({"power-saver": qsTr("Power Saver"), "balanced": qsTr("Balanced"),
                                          "performance": qsTr("Performance")})

    function batteryIcon(percent, charging) {
        const level = Math.max(0, Math.min(100, Math.round(percent / 10) * 10));
        return "battery-" + String(level).padStart(3, "0") + (charging ? "-charging" : "");
    }
    function pill(name) {
        const s = center.status;
        const t = bar.toggles;
        switch (name) {
        case "wifi":
            return s && s.net && s.net.wifiAvailable
                ? {available: true, label: qsTr("Wi-Fi"), sub: s.net.label, on: s.net.on,
                   icon: s.net.on ? "network-wireless" : "network-wireless-disconnected"}
                : {available: false};
        case "bluetooth":
            return s && s.bt && s.bt.available
                ? {available: true, label: qsTr("Bluetooth"), sub: s.bt.label, on: s.bt.on,
                   icon: s.bt.on ? "network-bluetooth" : "network-bluetooth-inactive"}
                : {available: false};
        case "night":
            return {available: t.known === true, label: qsTr("Night Light"), sub: t.night ? qsTr("Warm") : qsTr("Off"),
                    on: t.night === true, icon: "redshift-status-on"};
        case "power": {
            const profile = bar.battery.profile;
            return {available: bar.battery.profiles.length > 0, label: qsTr("Power"),
                    sub: center.profileNames[profile] || profile, on: profile === "performance",
                    icon: profile === "performance" ? "speedometer" : profile === "power-saver"
                        ? "battery-profile-powersave" : "battery-profile-balanced"};
        }
        case "dark":
            return {available: t.known === true, label: qsTr("Dark Style"), sub: t.dark ? qsTr("On") : qsTr("Off"),
                    on: t.dark === true, icon: "weather-clear-night"};
        case "dnd":
            return {available: !!center.notices, label: qsTr("Do Not Disturb"),
                    sub: center.notices && center.notices.doNotDisturb ? qsTr("On") : qsTr("Off"),
                    on: !!center.notices && center.notices.doNotDisturb, icon: "notifications-disabled"};
        case "aurora":
            return {available: t.known === true, label: qsTr("Aurora"), sub: t.aurora ? qsTr("Animated") : qsTr("Still"),
                    on: t.aurora === true, icon: "preferences-desktop-wallpaper"};
        }
        return {available: false};
    }
    function toggle(name) {
        const s = center.status;
        if (name === "wifi" && s && s.net) {
            s.net.toggle();
        } else if (name === "bluetooth" && s && s.bt) {
            s.bt.toggle();
        } else if (name === "night") {
            bar.toggleNightLight();
        } else if (name === "power") {
            const order = bar.battery.profiles;
            bar.battery.setProfile(order[(Math.max(0, order.indexOf(bar.battery.profile)) + 1) % order.length]);
        } else if (name === "dark") {
            bar.toggleDarkStyle();
        } else if (name === "dnd" && center.notices) {
            center.notices.setDoNotDisturb(center.notices.doNotDisturb ? 0 : 60);
        } else if (name === "aurora") {
            bar.toggleAurora();
        }
    }

    width: 400
    height: column.implicitHeight + 32
    focus: true
    Keys.onEscapePressed: dismissed()

    ColumnLayout {
        id: column
        x: 16
        y: 16
        width: center.width - 32
        spacing: 12

        RowLayout {
            Layout.fillWidth: true
            spacing: 10
            Kirigami.Icon {
                visible: bar.battery.present
                source: center.batteryIcon(bar.battery.percent, bar.battery.charging)
                Layout.preferredWidth: 22
                Layout.preferredHeight: 22
            }
            ColumnLayout {
                visible: bar.battery.present
                spacing: 0
                Text {
                    text: bar.battery.percent + "%"
                    font.bold: true
                    font.pointSize: Kirigami.Theme.defaultFont.pointSize
                    color: Kirigami.Theme.textColor
                }
                Text {
                    text: bar.battery.status
                    font.pointSize: Kirigami.Theme.smallFont.pointSize
                    color: Kirigami.Theme.disabledTextColor
                }
            }
            Item {
                Layout.fillWidth: true
            }
            IconButton {
                iconName: "preferences-system"
                tip: qsTr("System Settings")
                onClicked: {
                    center.dismissed();
                    bar.launch("systemsettings");
                }
            }
            IconButton {
                iconName: "system-lock-screen"
                tip: qsTr("Lock Screen")
                onClicked: {
                    center.dismissed();
                    bar.sessionRequested("lock");
                }
            }
            IconButton {
                iconName: "system-shutdown"
                tip: qsTr("Shut Down, Restart or Log Out")
                onClicked: {
                    center.dismissed();
                    bar.sessionRequested("shutdown");
                }
            }
        }

        SliderRow {
            Layout.fillWidth: true
            visible: !!center.status && !!center.status.brightness && center.status.brightness.available
            iconName: "brightness-high"
            value: visible ? center.status.brightness.fraction : 0
            onMoved: value => center.status.brightness.setFraction(value)
        }

        SliderRow {
            Layout.fillWidth: true
            visible: !!center.status && !!center.status.sound && center.status.sound.available
            iconName: visible ? center.status.sound.iconName : "audio-volume-high"
            value: visible ? center.status.sound.volume : 0
            dimmed: visible && center.status.sound.muted
            onMoved: value => center.status.sound.setVolume(value)
            onIconClicked: center.status.sound.toggleMute()
        }

        GridLayout {
            Layout.fillWidth: true
            columns: 2
            rowSpacing: 8
            columnSpacing: 8
            Repeater {
                model: center.cfg.pills
                delegate: Pill {
                    required property string modelData
                    readonly property var info: center.pill(modelData)
                    Layout.fillWidth: true
                    Layout.preferredWidth: 1
                    visible: info.available === true
                    label: info.label || ""
                    sub: info.sub || ""
                    iconName: info.icon || ""
                    on: info.on === true
                    onToggled: center.toggle(modelData)
                }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            visible: center.cfg.media && bar.media.available
            implicitHeight: 64
            radius: 14
            color: Qt.rgba(center.fg.r, center.fg.g, center.fg.b, 0.06)

            RowLayout {
                anchors.fill: parent
                anchors.margins: 10
                spacing: 10
                Item {
                    Layout.preferredWidth: 44
                    Layout.preferredHeight: 44
                    Image {
                        id: art
                        anchors.fill: parent
                        source: bar.media.artUrl
                        sourceSize: Qt.size(88, 88)
                        fillMode: Image.PreserveAspectCrop
                        visible: status === Image.Ready
                    }
                    Kirigami.Icon {
                        anchors.fill: parent
                        visible: art.status !== Image.Ready
                        source: bar.media.icon
                    }
                }
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 0
                    Text {
                        Layout.fillWidth: true
                        text: bar.media.title || bar.media.identity
                        textFormat: Text.PlainText
                        elide: Text.ElideRight
                        font.bold: true
                        font.pointSize: Kirigami.Theme.defaultFont.pointSize
                        color: Kirigami.Theme.textColor
                    }
                    Text {
                        Layout.fillWidth: true
                        text: bar.media.artist
                        textFormat: Text.PlainText
                        elide: Text.ElideRight
                        font.pointSize: Kirigami.Theme.smallFont.pointSize
                        color: Kirigami.Theme.disabledTextColor
                    }
                }
                IconButton {
                    iconName: "media-skip-backward"
                    tip: qsTr("Previous")
                    opacity: bar.media.canPrevious ? 1 : 0.4
                    onClicked: bar.media.previous()
                }
                IconButton {
                    iconName: bar.media.playing ? "media-playback-pause" : "media-playback-start"
                    tip: bar.media.playing ? qsTr("Pause") : qsTr("Play")
                    onClicked: bar.media.playPause()
                }
                IconButton {
                    iconName: "media-skip-forward"
                    tip: qsTr("Next")
                    opacity: bar.media.canNext ? 1 : 0.4
                    onClicked: bar.media.next()
                }
            }
        }
    }
}
