/*
    The Control Center's Sound page: where sound goes, how loud each app
    plays, and which microphone listens.
    SPDX-License-Identifier: GPL-3.0-or-later
*/
import QtQuick
import QtQuick.Layouts
import org.kde.kirigami as Kirigami
import ".."

ColumnLayout {
    id: page

    required property var center
    readonly property var sound: center.status ? center.status.sound : null

    // an app's name, and what it plays when that says more than "Playback"
    function streamName(model) {
        const parts = [];
        const client = model.Client;
        if (client && client.name && client.name !== "pipewire-media-session") {
            parts.push(client.name);
        } else if (model.Name) {
            parts.push(model.Name);
        }
        const media = model.Properties ? model.Properties["media.name"] : "";
        if (media && !/playback|audio|stream|alsa|pulse|pipewire/i.test(media) && parts.indexOf(media) < 0) {
            parts.push(media);
        }
        return parts.length > 0 ? parts.join(" · ") : qsTr("An app");
    }

    spacing: 6

    Component.onCompleted: if (sound) {
        sound.watchDevices(true);
    }
    Component.onDestruction: if (sound) {
        sound.watchDevices(false);
    }

    PageHeader {
        Layout.fillWidth: true
        title: qsTr("Sound")
        onBack: page.center.back()
    }

    Text {
        Layout.fillWidth: true
        Layout.margins: 10
        visible: !page.sound
        text: qsTr("Sound isn't available.")
        horizontalAlignment: Text.AlignHCenter
        color: Kirigami.Theme.disabledTextColor
    }

    Flickable {
        id: scroller
        Layout.fillWidth: true
        Layout.preferredHeight: Math.min(body.implicitHeight, Math.max(160, page.center.maxHeight - 130))
        visible: !!page.sound
        contentWidth: width
        contentHeight: body.implicitHeight
        clip: true
        interactive: contentHeight > height
        boundsBehavior: Flickable.StopAtBounds

        ColumnLayout {
            id: body
            width: scroller.width
            spacing: 2

            SectionLabel {
                text: qsTr("Output")
            }
            SliderRow {
                objectName: "output-volume"
                Layout.fillWidth: true
                Layout.leftMargin: 4
                visible: !!page.sound && page.sound.available
                iconName: page.sound ? page.sound.iconName : ""
                tip: page.sound && page.sound.muted ? qsTr("Unmute") : qsTr("Mute")
                value: page.sound ? page.sound.volume : 0
                dimmed: !!page.sound && page.sound.muted
                onMoved: value => page.sound.setVolume(value)
                onIconClicked: page.sound.toggleMute()
            }
            Repeater {
                model: page.sound ? page.sound.outputs : null
                delegate: ListRow {
                    required property var model
                    required property int index
                    objectName: "output-" + index
                    Layout.fillWidth: true
                    iconName: model.IconName || "audio-speakers"
                    title: model.Description || model.Name || ""
                    checked: model.Default === true
                    onClicked: page.sound.makeDefault(model.PulseObject)
                }
            }

            SectionLabel {
                visible: apps.count > 0
                text: qsTr("Apps")
            }
            Repeater {
                id: apps
                model: page.sound ? page.sound.streams : null
                delegate: ColumnLayout {
                    id: stream
                    required property var model
                    required property int index
                    readonly property real level: page.sound ? model.Volume / page.sound.normalVolume : 0
                    Layout.fillWidth: true
                    spacing: 0

                    RowLayout {
                        Layout.fillWidth: true
                        Layout.leftMargin: 10
                        Layout.topMargin: 4
                        spacing: 8
                        Kirigami.Icon {
                            source: stream.model.IconName || "applications-multimedia"
                            Layout.preferredWidth: 16
                            Layout.preferredHeight: 16
                        }
                        Text {
                            Layout.fillWidth: true
                            text: page.streamName(stream.model)
                            textFormat: Text.PlainText
                            elide: Text.ElideRight
                            font.pointSize: Kirigami.Theme.smallFont.pointSize
                            color: Kirigami.Theme.textColor
                        }
                    }
                    SliderRow {
                        objectName: "stream-" + stream.index
                        Layout.fillWidth: true
                        Layout.leftMargin: 4
                        visible: stream.model.HasVolume !== false
                        iconName: page.sound ? page.sound.iconFor(stream.level, stream.model.Muted === true, "audio-volume") : ""
                        tip: stream.model.Muted ? qsTr("Unmute") : qsTr("Mute")
                        value: stream.level
                        dimmed: stream.model.Muted === true
                        onMoved: value => page.sound.setObjectVolume(stream.model.PulseObject, value)
                        onIconClicked: page.sound.toggleObjectMute(stream.model.PulseObject)
                    }
                }
            }

            SectionLabel {
                visible: inputs.count > 0
                text: qsTr("Input")
            }
            SliderRow {
                objectName: "input-volume"
                Layout.fillWidth: true
                Layout.leftMargin: 4
                visible: !!page.sound && page.sound.micAvailable
                iconName: page.sound ? page.sound.micIconName : ""
                tip: page.sound && page.sound.micMuted ? qsTr("Turn the microphone on") : qsTr("Mute the microphone")
                value: page.sound ? page.sound.micVolume : 0
                dimmed: !!page.sound && page.sound.micMuted
                onMoved: value => page.sound.setMicVolume(value)
                onIconClicked: page.sound.toggleMicMute()
            }
            Repeater {
                id: inputs
                model: page.sound ? page.sound.inputs : null
                delegate: ListRow {
                    required property var model
                    required property int index
                    objectName: "input-" + index
                    Layout.fillWidth: true
                    iconName: model.IconName || "audio-input-microphone"
                    title: model.Description || model.Name || ""
                    checked: model.Default === true
                    onClicked: page.sound.makeDefault(model.PulseObject)
                }
            }
        }
    }

    RowLayout {
        Layout.fillWidth: true
        Item {
            Layout.fillWidth: true
        }
        TextButton {
            text: qsTr("Sound Settings…")
            onClicked: {
                page.center.dismissed();
                bar.openKcm("kcm_pulseaudio");
            }
        }
    }
}
