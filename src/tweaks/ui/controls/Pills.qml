/*
    The Control Center's toggles as the Tweaks pages name and draw them.
    SPDX-License-Identifier: GPL-3.0-or-later
*/
import QtQml

QtObject {
    readonly property var names: ({
        wifi: qsTr("Wi-Fi"), bluetooth: qsTr("Bluetooth"), night: qsTr("Night Light"), power: qsTr("Power Mode"),
        dark: qsTr("Dark Style"), dnd: qsTr("Do Not Disturb"), aurora: qsTr("Aurora"), awake: qsTr("Stay Awake"),
        airplane: qsTr("Airplane Mode"), hotspot: qsTr("Hotspot"), mic: qsTr("Microphone"),
        keyboard: qsTr("Keyboard Light"), screenshot: qsTr("Screenshot"), record: qsTr("Record Screen")
    })
    readonly property var icons: ({
        wifi: "network-wireless", bluetooth: "network-bluetooth", night: "redshift-status-on",
        power: "speedometer", dark: "weather-clear-night", dnd: "notifications-disabled",
        aurora: "preferences-desktop-wallpaper", awake: "system-suspend-inhibited", airplane: "network-flightmode-on",
        hotspot: "network-wireless-hotspot", mic: "audio-input-microphone", keyboard: "input-keyboard-brightness",
        screenshot: "camera-photo", record: "media-record"
    })
    readonly property var hints: ({
        wifi: qsTr("On or off; its arrow lists networks"), bluetooth: qsTr("On or off; its arrow lists devices"),
        night: qsTr("Warmer colours after dark"), power: qsTr("Power Saver, Balanced or Performance"),
        dark: qsTr("Borealis Dark or Light"), dnd: qsTr("No banners; its arrow sets for how long"),
        aurora: qsTr("The wallpaper animated or still"), awake: qsTr("No sleeping or locking by itself"),
        airplane: qsTr("Wi-Fi and Bluetooth off together"), hotspot: qsTr("Share this computer's connection"),
        mic: qsTr("Mute or unmute the microphone"), keyboard: qsTr("Step through the keyboard's light"),
        screenshot: qsTr("A region, a window or the screen"), record: qsTr("Record a region, a window or the screen")
    })
}
