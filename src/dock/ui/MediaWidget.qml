/*
    Now playing: the album art (or the player's icon), with a play/pause mark.
    Click to play or pause; right-click for the track, skipping and players.
    SPDX-License-Identifier: GPL-3.0-or-later
*/
import QtQuick
import QtQuick.Effects
import org.kde.kirigami as Kirigami

Item {
    id: widget

    readonly property var media: dock.media
    readonly property string label: media.title
        ? (media.artist ? media.title + " — " + media.artist : media.title)
        : media.identity

    Rectangle {
        id: plate
        anchors.fill: parent
        anchors.margins: parent.width * 0.05
        radius: width * 0.24
        gradient: Gradient {
            GradientStop { position: 0.0; color: Qt.darker(Kirigami.Theme.highlightColor, 1.4) }
            GradientStop { position: 1.0; color: Qt.darker(Kirigami.Theme.highlightColor, 2.4) }
        }
        Kirigami.Icon {
            anchors.centerIn: parent
            width: parent.width * 0.62
            height: width
            source: widget.media.icon
            visible: art.status !== Image.Ready
        }
    }

    Image {
        id: art
        anchors.fill: plate
        source: widget.media.artUrl
        sourceSize.width: 256
        sourceSize.height: 256
        fillMode: Image.PreserveAspectCrop
        asynchronous: true
        visible: false
    }
    Rectangle {
        id: mask
        anchors.fill: plate
        radius: plate.radius
        visible: false
        layer.enabled: true
    }
    MultiEffect {
        anchors.fill: plate
        source: art
        visible: art.status === Image.Ready
        maskEnabled: true
        maskSource: mask
        maskThresholdMin: 0.5
        maskSpreadAtMin: 1.0
        opacity: widget.media.playing ? 1 : 0.7
    }

    Rectangle {
        width: plate.width * 0.42
        height: width
        radius: width / 2
        x: plate.x + plate.width - width * 0.8
        y: plate.y + plate.height - width * 0.8
        color: Qt.rgba(0.05, 0.06, 0.1, 0.85)
        border.width: Math.max(1, width * 0.05)
        border.color: Qt.rgba(1, 1, 1, 0.35)
        Kirigami.Icon {
            anchors.centerIn: parent
            width: parent.width * 0.58
            height: width
            source: widget.media.playing ? "media-playback-pause" : "media-playback-start"
            color: "white"
            isMask: true
        }
    }
}
