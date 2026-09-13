/*
    Borealis Bar: a bar on each screen it lives on, the overlay its menus and
    panels open in, and notification banners.
    SPDX-License-Identifier: GPL-3.0-or-later
*/
import QtQuick
import QtQml

QtObject {
    id: root

    // the parts that lean on Plasma's own modules load on their own, so a
    // missing or changed module switches off just that part
    function load(file) {
        const component = Qt.createComponent(file);
        if (component.status !== Component.Ready) {
            console.warn("bar:", file, "is unavailable:", component.errorString());
            return null;
        }
        return component.createObject(root);
    }

    readonly property var notices: load("NotificationCenter.qml")
    readonly property var sessions: load("Sessions.qml")
    readonly property var status: load("Status.qml")

    property var bars: Instantiator {
        model: bar.screens
        delegate: BarWindow {
            required property var modelData
            targetScreen: modelData
            notices: root.notices
            status: root.status
        }
    }

    property var overlay: Overlay {
        notices: root.notices
        status: root.status
    }

    property var banners: Banners {
        notices: root.notices
    }

    property var sessionActions: Connections {
        target: bar
        function onSessionRequested(action) {
            if (root.sessions) {
                root.sessions.run(action);
            }
        }
    }
}
