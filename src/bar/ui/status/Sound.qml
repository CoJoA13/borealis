/*
    Sound, from Plasma's volume module: the default output and input, and
    (while a page shows them) every output, input and app playing sound.
    SPDX-License-Identifier: GPL-3.0-or-later
*/
import QtQuick
import org.kde.kitemmodels as KItemModels
import org.kde.plasma.private.volume

QtObject {
    id: sound

    property var sinks: SinkModel {}
    property var sources: SourceModel {}
    // the defaults, for when PreferredDevice hasn't settled yet
    property var fallbackSink: null
    property var fallbackSource: null
    property var sinkFinder: Instantiator {
        model: sound.sinks
        delegate: QtObject {
            required property var model
            readonly property bool isDefault: model.Default === true
            onIsDefaultChanged: if (isDefault) {
                sound.fallbackSink = model.PulseObject;
            }
            Component.onCompleted: if (isDefault) {
                sound.fallbackSink = model.PulseObject;
            }
        }
    }
    property var sourceFinder: Instantiator {
        model: sound.sources
        delegate: QtObject {
            required property var model
            readonly property bool isDefault: model.Default === true
            onIsDefaultChanged: if (isDefault) {
                sound.fallbackSource = model.PulseObject;
            }
            Component.onCompleted: if (isDefault) {
                sound.fallbackSource = model.PulseObject;
            }
        }
    }

    readonly property real normalVolume: PulseAudio.NormalVolume

    readonly property var sink: PreferredDevice.sink || fallbackSink
    readonly property bool available: !!sink
    readonly property real volume: sink ? sink.volume / PulseAudio.NormalVolume : 0
    readonly property bool muted: sink ? sink.muted : false
    readonly property string deviceName: sink ? sink.description : ""
    readonly property string iconName: iconFor(volume, muted, "audio-volume")

    readonly property var source: PreferredDevice.source || fallbackSource
    readonly property bool micAvailable: !!source
    readonly property real micVolume: source ? source.volume / PulseAudio.NormalVolume : 0
    readonly property bool micMuted: source ? source.muted : false
    readonly property string micName: source ? source.description : ""
    readonly property string micIconName: iconFor(micVolume, micMuted, "microphone-sensitivity")

    function iconFor(level, mute, stem) {
        return mute || level <= 0.001 ? stem + "-muted"
            : level < 0.34 ? stem + "-low" : level < 0.67 ? stem + "-medium" : stem + "-high";
    }
    function setVolume(fraction) {
        setObjectVolume(sink, fraction);
    }
    function toggleMute() {
        toggleObjectMute(sink);
    }
    function setMicVolume(fraction) {
        setObjectVolume(source, fraction);
    }
    function toggleMicMute() {
        toggleObjectMute(source);
    }
    // any device or app stream
    function setObjectVolume(object, fraction) {
        if (!object) {
            return;
        }
        object.muted = false;
        object.volume = Math.round(Math.max(0, Math.min(1, fraction)) * PulseAudio.NormalVolume);
    }
    function toggleObjectMute(object) {
        if (object) {
            object.muted = !object.muted;
        }
    }
    function makeDefault(object) {
        if (object) {
            object.default = true;
        }
    }

    // real devices that are plugged in, and whichever one is the default
    property Component devicesComponent: Component {
        KItemModels.KSortFilterProxyModel {
            filterRowCallback: function (row, parent) {
                const index = sourceModel.index(row, 0, parent);
                const roles = sourceModel.KItemModels.KRoleNames;
                if (sourceModel.data(index, roles.role("Name")) === "auto_null") {
                    return false;
                }
                if (sourceModel.data(index, roles.role("Default")) === true) {
                    return true;
                }
                const device = sourceModel.data(index, roles.role("PulseObject"));
                if (!device || device.virtualDevice) {
                    return false;
                }
                const ports = device.ports || [];
                return !(ports.length === 1 && ports[0].availability === Port.Unavailable);
            }
        }
    }
    // apps playing sound (not the desktop's own event sounds)
    property Component streamsComponent: Component {
        KItemModels.KSortFilterProxyModel {
            sourceModel: SinkInputModel {}
            filterRowCallback: function (row, parent) {
                const index = sourceModel.index(row, 0, parent);
                const roles = sourceModel.KItemModels.KRoleNames;
                if (sourceModel.data(index, roles.role("VirtualStream")) === true) {
                    return false;
                }
                const client = sourceModel.data(index, roles.role("Client"));
                return !client || client.name !== "libcanberra";
            }
        }
    }

    property int watching: 0
    property var outputs: null
    property var inputs: null
    property var streams: null
    function watchDevices(watch) {
        watching = Math.max(0, watching + (watch ? 1 : -1));
        if (watching > 0 && !outputs) {
            outputs = devicesComponent.createObject(sound, {sourceModel: sinks});
            inputs = devicesComponent.createObject(sound, {sourceModel: sources});
            streams = streamsComponent.createObject(sound);
        } else if (watching === 0 && outputs) {
            const old = [outputs, inputs, streams];
            outputs = inputs = streams = null;
            old.forEach(model => model.destroy(1000));
        }
    }
}
