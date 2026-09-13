/*
    The Control Center: battery and session buttons, sliders, the toggles (in
    the order the settings give) and what's playing. A toggle with more to it
    has an arrow that slides its page in; edit mode picks and arranges the
    toggles, and the bar's settings file keeps them.
    SPDX-License-Identifier: GPL-3.0-or-later
*/
import QtQuick
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

Card {
    id: center

    property var status: null
    property var notices: null
    property real maxHeight: 900
    signal dismissed()

    // the page on show ("" for the front), and the one loaded (which stays
    // while it slides away)
    property string page: ""
    property string shownPage: ""
    property bool editing: false
    // the toggles while editing, in their new order
    property var draft: []

    readonly property var cfg: bar.settings.values
    readonly property real innerWidth: width - 32
    readonly property var pageFiles: ({
        wifi: "pages/WifiPage.qml", bluetooth: "pages/BluetoothPage.qml", sound: "pages/SoundPage.qml",
        power: "pages/PowerPage.qml", dnd: "pages/DndPage.qml", hotspot: "pages/HotspotPage.qml",
        screenshot: "pages/CapturePage.qml", record: "pages/CapturePage.qml"
    })
    readonly property var names: ({
        wifi: qsTr("Wi-Fi"), bluetooth: qsTr("Bluetooth"), night: qsTr("Night Light"), power: qsTr("Power Mode"),
        dark: qsTr("Dark Style"), dnd: qsTr("Do Not Disturb"), aurora: qsTr("Aurora"), awake: qsTr("Stay Awake"),
        airplane: qsTr("Airplane Mode"), hotspot: qsTr("Hotspot"), mic: qsTr("Microphone"),
        keyboard: qsTr("Keyboard Light"), screenshot: qsTr("Screenshot"), record: qsTr("Record Screen")
    })
    readonly property var icons: ({
        wifi: "network-wireless", bluetooth: "network-bluetooth", night: "redshift-status-on",
        power: "speedometer", dark: "weather-clear-night", dnd: "notifications-disabled",
        aurora: "preferences-desktop-wallpaper", awake: "system-suspend-uninhibited", airplane: "network-flightmode-on",
        hotspot: "network-wireless-hotspot", mic: "audio-input-microphone", keyboard: "input-keyboard-brightness",
        screenshot: "camera-photo", record: "media-record"
    })
    readonly property var profileNames: ({"power-saver": qsTr("Power Saver"), "balanced": qsTr("Balanced"),
                                          "performance": qsTr("Performance")})

    // power modes from Plasma's module when it loaded, else straight from the daemon
    readonly property var power: status && status.power && status.power.profilesAvailable ? status.power : null
    readonly property var profiles: power ? power.profiles : bar.battery.profiles
    readonly property string profile: power ? power.profile : bar.battery.profile

    readonly property var shownPills: cfg.pills.filter(name => pill(name).available === true)
    readonly property var addable: editing
        ? bar.allPills.filter(name => draft.indexOf(name) < 0 && pill(name).available === true) : []

    function batteryIcon(percent, charging) {
        const level = Math.max(0, Math.min(100, Math.round(percent / 10) * 10));
        return "battery-" + String(level).padStart(3, "0") + (charging ? "-charging" : "");
    }
    function profileIcon(name) {
        return name === "performance" ? "battery-profile-performance"
            : name === "power-saver" ? "battery-profile-powersave" : "speedometer";
    }
    function setProfile(name) {
        if (center.power) {
            center.power.setProfile(name);
        } else {
            bar.battery.setProfile(name);
        }
    }
    function forever() {
        const date = new Date();
        date.setFullYear(date.getFullYear() + 1);
        return date;
    }

    // --- pages and edit mode ------------------------------------------------
    function openPage(name) {
        if (!center.pageFiles[name]) {
            return;
        }
        center.editing = false;
        if (center.shownPage !== name || !pageView.item) {
            pageView.source = "";
            center.shownPage = name;
            pageView.setSource(Qt.resolvedUrl(center.pageFiles[name]), {center: center});
        }
        center.page = name;
    }
    function back() {
        center.page = "";
        center.forceActiveFocus();
    }
    function reset() {
        center.page = "";
        center.editing = false;
        center.shownPage = "";
        pageView.source = "";
    }
    onVisibleChanged: if (!visible) {
        reset();
    }
    onPageChanged: bar.reportControls(page, editing)
    onEditingChanged: {
        if (editing) {
            draft = cfg.pills.slice();
        }
        bar.reportControls(page, editing);
    }
    Connections {
        target: bar
        function onControlsPageRequested(name) {
            if (name === "edit") {
                center.back();
                center.editing = true;
            } else if (name === "") {
                center.back();
            } else {
                center.openPage(name);
            }
        }
    }

    function dragPill(name, cx, cy) {
        const from = center.draft.indexOf(name);
        if (from < 0) {
            return;
        }
        const column = cx < grid.width / 2 ? 0 : 1;
        const row = Math.max(0, Math.floor((cy + 4) / (grid.cellHeight + 8)));
        const to = Math.max(0, Math.min(center.draft.length - 1, row * 2 + column));
        if (to !== from) {
            const next = center.draft.slice();
            next.splice(to, 0, next.splice(from, 1)[0]);
            center.draft = next;
        }
    }
    function savePills() {
        if (JSON.stringify(center.draft) !== JSON.stringify(center.cfg.pills)) {
            bar.settings.set("pills", center.draft);
        }
    }
    function removePill(name) {
        center.draft = center.draft.filter(n => n !== name);
        savePills();
    }
    function addPill(name) {
        if (center.draft.indexOf(name) < 0) {
            center.draft = center.draft.concat([name]);
            savePills();
        }
    }

    // --- what each toggle shows and does ------------------------------------
    function pill(name) {
        const s = center.status;
        const t = bar.toggles;
        const none = {available: false};
        switch (name) {
        case "wifi":
            if (!s || !s.net || !s.net.wifiAvailable) {
                return none;
            }
            return {available: true, sub: s.net.label, on: s.net.on && !s.net.airplane, page: "wifi",
                    icon: s.net.on && !s.net.airplane ? "network-wireless" : "network-wireless-disconnected"};
        case "bluetooth":
            if (!s || !s.bt || !s.bt.available) {
                return none;
            }
            return {available: true, sub: s.bt.label, on: s.bt.on, page: "bluetooth",
                    icon: s.bt.on ? "network-bluetooth" : "network-bluetooth-inactive"};
        case "night":
            return {available: t.known === true, sub: t.night ? qsTr("Warm") : qsTr("Off"), on: t.night === true};
        case "power":
            return {available: center.profiles.length > 0, on: center.profile !== "" && center.profile !== "balanced",
                    sub: center.profileNames[center.profile] || center.profile, icon: center.profileIcon(center.profile),
                    page: "power"};
        case "dark":
            return {available: t.known === true, sub: t.dark ? qsTr("On") : qsTr("Off"), on: t.dark === true};
        case "dnd": {
            const quiet = !!center.notices && center.notices.doNotDisturb;
            return {available: !!center.notices, sub: quiet ? qsTr("On") : qsTr("Off"), on: quiet, page: "dnd"};
        }
        case "aurora":
            return {available: t.known === true, sub: t.aurora ? qsTr("Animated") : qsTr("Still"), on: t.aurora === true};
        case "awake":
            if (!s || !s.power) {
                return none;
            }
            return {available: true, sub: s.power.awake ? qsTr("On") : qsTr("Off"), on: s.power.awake,
                    icon: s.power.awake ? "system-suspend-inhibited" : "system-suspend-uninhibited"};
        case "airplane":
            if (!s || !s.net || !s.net.airplaneAvailable) {
                return none;
            }
            return {available: true, sub: s.net.airplane ? qsTr("On") : qsTr("Off"), on: s.net.airplane};
        case "hotspot":
            if (!s || !s.net || !s.net.wifiAvailable) {
                return none;
            }
            return {available: true, on: s.net.hotspotActive, page: "hotspot",
                    sub: s.net.hotspotActive ? s.net.hotspotName : !s.net.on || s.net.airplane ? qsTr("Wi-Fi is off")
                        : !s.net.hotspotSupported ? qsTr("Wi-Fi is busy") : qsTr("Off")};
        case "mic":
            if (!s || !s.sound || !s.sound.micAvailable) {
                return none;
            }
            return {available: true, sub: s.sound.micMuted ? qsTr("Muted") : qsTr("On"), on: !s.sound.micMuted,
                    icon: s.sound.micMuted ? "microphone-sensitivity-muted" : "audio-input-microphone", page: "sound"};
        case "keyboard":
            if (!s || !s.keyboard || !s.keyboard.available) {
                return none;
            }
            return {available: true, sub: s.keyboard.label, on: s.keyboard.level > 0};
        case "screenshot":
            return {available: bar.canCapture, sub: qsTr("Region"), page: "screenshot"};
        case "record":
            return {available: bar.canCapture, sub: qsTr("Region"), page: "record"};
        }
        return none;
    }
    function toggle(name) {
        if (pill(name).available !== true) {
            return;
        }
        const s = center.status;
        switch (name) {
        case "wifi":
            if (s.net.airplane) {
                s.net.setAirplane(false);
            } else {
                s.net.toggle();
            }
            break;
        case "bluetooth":
            s.bt.toggle();
            break;
        case "night":
            bar.toggleNightLight();
            break;
        case "power": {
            const order = center.profiles;
            center.setProfile(order[(Math.max(0, order.indexOf(center.profile)) + 1) % order.length]);
            break;
        }
        case "dark":
            bar.toggleDarkStyle();
            break;
        case "dnd":
            if (center.notices.doNotDisturb) {
                center.notices.setDoNotDisturb(0);
            } else {
                center.notices.setDoNotDisturbUntil(center.forever());
            }
            break;
        case "aurora":
            bar.toggleAurora();
            break;
        case "awake":
            s.power.setAwake(!s.power.awake);
            break;
        case "airplane":
            s.net.setAirplane(!s.net.airplane);
            break;
        case "hotspot":
            if (s.net.hotspotActive) {
                s.net.stopHotspot();
            } else if (s.net.hotspotSupported && s.net.hotspotName !== "" && s.net.hotspotPassword.length >= 8) {
                s.net.startHotspot(s.net.hotspotName, s.net.hotspotPassword);
            } else {
                center.openPage("hotspot");
            }
            break;
        case "mic":
            s.sound.toggleMicMute();
            break;
        case "keyboard":
            s.keyboard.cycle();
            break;
        case "screenshot":
            bar.capture("region");
            break;
        case "record":
            bar.capture("record-region");
            break;
        }
    }

    function slider(name) {
        const s = center.status;
        switch (name) {
        case "brightness":
            return s && s.brightness && s.brightness.available
                ? {available: true, icon: "brightness-high", value: s.brightness.fraction, tip: qsTr("Screen brightness")}
                : {available: false};
        case "volume":
            return s && s.sound && s.sound.available
                ? {available: true, icon: s.sound.iconName, value: s.sound.volume, dimmed: s.sound.muted, page: "sound",
                   tip: s.sound.muted ? qsTr("Unmute") : qsTr("Mute")}
                : {available: false};
        case "microphone":
            return s && s.sound && s.sound.micAvailable
                ? {available: true, icon: s.sound.micIconName, value: s.sound.micVolume, dimmed: s.sound.micMuted,
                   page: "sound", tip: s.sound.micMuted ? qsTr("Turn the microphone on") : qsTr("Mute the microphone")}
                : {available: false};
        case "keyboard":
            return s && s.keyboard && s.keyboard.available
                ? {available: true, icon: "input-keyboard-brightness", value: s.keyboard.fraction,
                   tip: qsTr("Keyboard light")}
                : {available: false};
        }
        return {available: false};
    }
    function slide(name, value) {
        const s = center.status;
        if (name === "brightness") {
            s.brightness.setFraction(value);
        } else if (name === "volume") {
            s.sound.setVolume(value);
        } else if (name === "microphone") {
            s.sound.setMicVolume(value);
        } else if (name === "keyboard") {
            s.keyboard.setFraction(value);
        }
    }
    function sliderIcon(name) {
        if (name === "volume") {
            center.status.sound.toggleMute();
        } else if (name === "microphone") {
            center.status.sound.toggleMicMute();
        }
    }

    width: 420
    height: Math.min(page !== "" && pageView.item ? pageView.item.implicitHeight : front.implicitHeight,
                     maxHeight - 32) + 32
    Behavior on height {
        enabled: center.visible
        NumberAnimation {
            duration: 180
            easing.type: Easing.OutCubic
        }
    }
    focus: true
    Keys.onEscapePressed: {
        if (center.page !== "") {
            center.back();
        } else if (center.editing) {
            center.editing = false;
        } else {
            center.dismissed();
        }
    }

    Item {
        anchors.fill: parent
        clip: true

        ColumnLayout {
            id: front
            x: (center.page === "" ? 0 : -center.width) + 16
            y: 16
            width: center.innerWidth
            visible: x > 16 - center.width
            spacing: 12
            Behavior on x {
                enabled: center.visible
                NumberAnimation {
                    duration: 200
                    easing.type: Easing.OutCubic
                }
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: 8

                Rectangle {
                    objectName: "battery"
                    visible: bar.battery.present
                    implicitWidth: batteryRow.implicitWidth + 16
                    implicitHeight: 40
                    radius: 10
                    color: batteryHover.hovered ? Qt.rgba(center.fg.r, center.fg.g, center.fg.b, 0.08) : "transparent"
                    Accessible.name: qsTr("Power and battery")
                    Accessible.role: Accessible.Button

                    RowLayout {
                        id: batteryRow
                        anchors.centerIn: parent
                        spacing: 8
                        Kirigami.Icon {
                            source: center.batteryIcon(bar.battery.percent, bar.battery.charging)
                            Layout.preferredWidth: 22
                            Layout.preferredHeight: 22
                        }
                        ColumnLayout {
                            spacing: 0
                            Text {
                                text: bar.battery.percent + "%"
                                font.bold: true
                                font.pointSize: Kirigami.Theme.defaultFont.pointSize
                                font.features: { "tnum": 1 }
                                color: Kirigami.Theme.textColor
                            }
                            Text {
                                text: bar.battery.status
                                font.pointSize: Kirigami.Theme.smallFont.pointSize
                                color: Kirigami.Theme.disabledTextColor
                            }
                        }
                    }
                    HoverHandler {
                        id: batteryHover
                        cursorShape: Qt.PointingHandCursor
                    }
                    TapHandler {
                        onTapped: center.openPage("power")
                    }
                }
                Item {
                    Layout.fillWidth: true
                }
                IconButton {
                    objectName: "edit"
                    iconName: center.editing ? "dialog-ok-apply" : "document-edit"
                    checked: center.editing
                    tip: center.editing ? qsTr("Done") : qsTr("Edit the toggles")
                    onClicked: center.editing = !center.editing
                }
                IconButton {
                    visible: !center.editing
                    iconName: "configure"
                    tip: qsTr("System Settings")
                    onClicked: {
                        center.dismissed();
                        bar.launch("systemsettings");
                    }
                }
                IconButton {
                    visible: !center.editing
                    iconName: "system-lock-screen"
                    tip: qsTr("Lock Screen")
                    onClicked: {
                        center.dismissed();
                        bar.sessionRequested("lock");
                    }
                }
                IconButton {
                    visible: !center.editing
                    iconName: "system-shutdown"
                    tip: qsTr("Shut Down, Restart or Log Out")
                    onClicked: {
                        center.dismissed();
                        bar.sessionRequested("shutdown");
                    }
                }
            }

            Repeater {
                model: center.editing ? [] : center.cfg.sliders
                delegate: SliderRow {
                    required property string modelData
                    readonly property var info: center.slider(modelData)
                    objectName: "slider-" + modelData
                    Layout.fillWidth: true
                    visible: info.available === true
                    iconName: info.icon || ""
                    tip: info.tip || ""
                    value: info.value || 0
                    dimmed: info.dimmed === true
                    hasDetails: !!info.page
                    onMoved: value => center.slide(modelData, value)
                    onIconClicked: center.sliderIcon(modelData)
                    onDetailsRequested: center.openPage(info.page)
                }
            }

            Text {
                Layout.fillWidth: true
                visible: center.editing
                text: qsTr("Drag the toggles into the order you like. − takes one out.")
                wrapMode: Text.WordWrap
                font.pointSize: Kirigami.Theme.smallFont.pointSize
                color: Kirigami.Theme.disabledTextColor
            }

            // the toggles, two to a row; placed by hand so a dragged one can
            // move through the others
            Item {
                id: grid
                objectName: "pills"
                readonly property var names: center.editing ? center.draft : center.shownPills
                readonly property int rows: Math.ceil(names.length / 2)
                readonly property real cellWidth: (width - 8) / 2
                readonly property real cellHeight: 52
                Layout.fillWidth: true
                implicitHeight: rows > 0 ? rows * (cellHeight + 8) - 8 : 0
                visible: rows > 0

                Repeater {
                    model: bar.allPills
                    delegate: Item {
                        id: cell
                        required property string modelData
                        readonly property int slot: grid.names.indexOf(modelData)
                        readonly property var info: center.pill(modelData)
                        readonly property real restX: (slot % 2) * (grid.cellWidth + 8)
                        readonly property real restY: Math.floor(slot / 2) * (grid.cellHeight + 8)
                        // where a drag began: kept apart from restX/restY, which
                        // move as the dragged toggle passes the others
                        property real startX: 0
                        property real startY: 0
                        objectName: "pill-" + modelData
                        Component.onCompleted: {
                            startX = restX;
                            startY = restY;
                        }
                        visible: slot >= 0
                        width: grid.cellWidth
                        height: grid.cellHeight
                        z: dragger.active ? 2 : 0
                        x: dragger.active ? startX + dragger.activeTranslation.x : restX
                        y: dragger.active ? startY + dragger.activeTranslation.y : restY
                        onRestXChanged: if (!dragger.active) {
                            startX = restX;
                        }
                        onRestYChanged: if (!dragger.active) {
                            startY = restY;
                        }
                        Behavior on x {
                            enabled: center.editing && !dragger.active
                            NumberAnimation {
                                duration: 150
                                easing.type: Easing.OutCubic
                            }
                        }
                        Behavior on y {
                            enabled: center.editing && !dragger.active
                            NumberAnimation {
                                duration: 150
                                easing.type: Easing.OutCubic
                            }
                        }

                        Pill {
                            anchors.fill: parent
                            label: center.names[cell.modelData] || cell.modelData
                            sub: center.editing && cell.info.available !== true ? qsTr("Not on this computer")
                                : cell.info.sub || ""
                            iconName: cell.info.icon || center.icons[cell.modelData] || ""
                            on: cell.info.on === true
                            hasDetails: !!cell.info.page && cell.info.available === true
                            editing: center.editing
                            dimmed: center.editing && cell.info.available !== true
                            lifted: dragger.active
                            onToggled: center.toggle(cell.modelData)
                            onDetailsRequested: center.openPage(cell.info.page)
                            onRemoveRequested: center.removePill(cell.modelData)
                        }
                        DragHandler {
                            id: dragger
                            enabled: center.editing
                            target: null
                            onActiveChanged: if (!active) {
                                center.savePills();
                            }
                            onActiveTranslationChanged: if (active) {
                                center.dragPill(cell.modelData, cell.startX + activeTranslation.x + cell.width / 2,
                                                cell.startY + activeTranslation.y + cell.height / 2);
                            }
                        }
                    }
                }
            }

            ColumnLayout {
                Layout.fillWidth: true
                visible: center.editing
                spacing: 8

                SectionLabel {
                    Layout.leftMargin: 2
                    text: center.addable.length > 0 ? qsTr("Add") : qsTr("Every toggle this computer can use is in.")
                }
                Flow {
                    Layout.fillWidth: true
                    spacing: 6
                    Repeater {
                        model: center.addable
                        delegate: Rectangle {
                            id: chip
                            required property string modelData
                            objectName: "add-" + modelData
                            width: chipRow.implicitWidth + 24
                            height: 34
                            radius: 17
                            color: chipHover.hovered ? Qt.rgba(center.fg.r, center.fg.g, center.fg.b, 0.16)
                                                     : Qt.rgba(center.fg.r, center.fg.g, center.fg.b, 0.07)
                            Accessible.name: qsTr("Add %1").arg(center.names[modelData])
                            Accessible.role: Accessible.Button

                            Row {
                                id: chipRow
                                anchors.centerIn: parent
                                spacing: 6
                                Kirigami.Icon {
                                    anchors.verticalCenter: parent.verticalCenter
                                    source: "list-add"
                                    width: 14
                                    height: 14
                                }
                                Kirigami.Icon {
                                    anchors.verticalCenter: parent.verticalCenter
                                    source: center.pill(chip.modelData).icon || center.icons[chip.modelData]
                                    width: 16
                                    height: 16
                                }
                                Text {
                                    anchors.verticalCenter: parent.verticalCenter
                                    text: center.names[chip.modelData]
                                    font.pointSize: Kirigami.Theme.defaultFont.pointSize
                                    color: Kirigami.Theme.textColor
                                }
                            }
                            HoverHandler {
                                id: chipHover
                                cursorShape: Qt.PointingHandCursor
                            }
                            TapHandler {
                                onTapped: center.addPill(chip.modelData)
                            }
                        }
                    }
                }
                TextButton {
                    Layout.alignment: Qt.AlignRight
                    text: qsTr("More in %1 Tweaks…").arg(bar.name)
                    onClicked: {
                        center.dismissed();
                        bar.openTweaks("controls");
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                visible: !center.editing && center.cfg.media && bar.media.available
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

        Loader {
            id: pageView
            objectName: "pageView"
            x: (center.page === "" ? center.width : 0) + 16
            y: 16
            width: center.innerWidth
            visible: x < center.width + 16
            Behavior on x {
                enabled: center.visible
                NumberAnimation {
                    duration: 200
                    easing.type: Easing.OutCubic
                }
            }
            // once a page has slid all the way out, it goes
            onXChanged: if (center.page === "" && x >= center.width + 16 && status !== Loader.Null) {
                source = "";
                center.shownPage = "";
            }
        }
    }
}
