/*
    The sound output, from Plasma's volume module.
    SPDX-License-Identifier: GPL-3.0-or-later
*/
import QtQuick
import org.kde.plasma.private.volume

QtObject {
    id: sound

    property var sinks: SinkModel {}
    property var fallback: null
    // the default output, for when PreferredDevice hasn't settled yet
    property var finder: Instantiator {
        model: sound.sinks
        delegate: QtObject {
            required property var model
            readonly property bool isDefault: model.Default === true
            onIsDefaultChanged: if (isDefault) {
                sound.fallback = model.PulseObject;
            }
            Component.onCompleted: if (isDefault) {
                sound.fallback = model.PulseObject;
            }
        }
    }

    readonly property var sink: PreferredDevice.sink || fallback
    readonly property bool available: !!sink
    readonly property real volume: sink ? sink.volume / PulseAudio.NormalVolume : 0
    readonly property bool muted: sink ? sink.muted : false
    readonly property string deviceName: sink ? sink.description : ""
    readonly property string iconName: muted || volume <= 0.001 ? "audio-volume-muted"
        : volume < 0.34 ? "audio-volume-low" : volume < 0.67 ? "audio-volume-medium" : "audio-volume-high"

    function setVolume(fraction) {
        if (!sink) {
            return;
        }
        sink.muted = false;
        sink.volume = Math.round(Math.max(0, Math.min(1, fraction)) * PulseAudio.NormalVolume);
    }
    function toggleMute() {
        if (sink) {
            sink.muted = !sink.muted;
        }
    }
}
