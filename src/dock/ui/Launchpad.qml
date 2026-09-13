/*
    Launchpad: every app on one sheet of frosted glass. Type to search (the
    apps, then settings, sums and conversions from Plasma's runners); arrows
    and Return launch, Escape leaves. Pages turn with the wheel, a swipe or
    Page Up/Down; drag an app onto the dock to keep it there.
    SPDX-License-Identifier: GPL-3.0-or-later
*/
import QtQuick
import org.kde.kirigami as Kirigami
import org.kde.layershell as LayerShell

Window {
    id: pad

    readonly property var grid: dock.launchpadApps
    readonly property var apps: grid.items
    readonly property real anim: dock.settings.values.animation
    property var targetScreen: null
    property bool open: false
    property bool dragging: false
    property bool typed: false
    property int selected: -1
    property int commitTick: 0
    property real wheelSum: 0
    property bool wheelResting: false

    readonly property real iconSize: Math.round(Math.max(56, Math.min(96, height * 0.075)))
    readonly property real cellWidth: Math.round(iconSize * 2.1)
    readonly property real cellHeight: Math.round(iconSize * 1.8)
    readonly property real gridTop: searchBox.y + searchBox.height + Math.round(height * 0.05)
    readonly property int columns: Math.max(3, Math.min(8, Math.floor(width * 0.84 / cellWidth)))
    readonly property int rows: Math.max(2, Math.min(5, Math.floor((height - gridTop - 150) / cellHeight)))
    readonly property int perPage: columns * rows
    readonly property int pageCount: Math.max(1, Math.ceil(apps.length / perPage))
    readonly property var runnerResults: runners.item && search.text.length > 0 ? runners.item.results : []

    title: qsTr("Launchpad")
    color: "transparent"
    visible: false
    width: 1280
    height: 800

    LayerShell.Window.scope: "launchpad"
    LayerShell.Window.layer: LayerShell.Window.LayerOverlay
    LayerShell.Window.screen: targetScreen
    LayerShell.Window.anchors: LayerShell.Window.AnchorTop | LayerShell.Window.AnchorBottom
        | LayerShell.Window.AnchorLeft | LayerShell.Window.AnchorRight
    LayerShell.Window.exclusionZone: -1
    LayerShell.Window.keyboardInteractivity: LayerShell.Window.KeyboardInteractivityExclusive

    Connections {
        target: dock
        function onLaunchpadChanged() {
            if (dock.launchpadOpen && !pad.open) {
                pad.show();
            } else if (!dock.launchpadOpen && pad.open) {
                pad.hide();
            }
        }
    }

    function show() {
        closeTimer.stop();
        if (pad.visible && pad.targetScreen !== dock.launchpadScreen) {
            pad.visible = false;                // a fresh surface on the other screen
        }
        pad.targetScreen = dock.launchpadScreen;
        pad.dragging = false;
        menu.visible = false;
        search.text = "";
        pad.selected = -1;
        pages.currentIndex = 0;
        pad.visible = true;
        pad.open = true;
        search.forceActiveFocus();
        Qt.callLater(pad.pushSurface);
    }
    function hide() {
        pad.open = false;
        menu.visible = false;
        if (pad.anim > 0) {
            closeTimer.restart();               // after the fade
        } else {
            pad.visible = false;
        }
    }
    Timer {
        id: closeTimer
        interval: 200 * Math.max(0.2, pad.anim)
        onTriggered: if (!pad.open) {
            pad.visible = false;
        }
    }

    function pushSurface() {
        if (!pad.visible) {
            return;
        }
        if (pad.dragging) {
            // an app on its way to the dock: let the drop through to what's beneath
            dock.updateSurface(pad, [Qt.rect(0, 0, 1, 1)], Qt.rect(0, 0, 0, 0), -1);
        } else {
            dock.updateSurface(pad, [], Qt.rect(0, 0, pad.width, pad.height), 0);
        }
    }
    onVisibleChanged: if (visible) {
        Qt.callLater(pad.pushSurface);
        Qt.callLater(() => search.forceActiveFocus());
    }
    onWidthChanged: Qt.callLater(pad.pushSurface)
    onHeightChanged: Qt.callLater(pad.pushSurface)
    onDraggingChanged: Qt.callLater(pad.pushSurface)

    function launch(appId) {
        dock.launchApp(appId);
    }
    function runResult(result) {
        if (runners.item) {
            runners.item.run(result);
        }
        dock.setLaunchpadOpen(false);
    }
    function select(i) {
        if (pad.apps.length === 0) {
            pad.selected = -1;
            return;
        }
        pad.selected = Math.max(0, Math.min(pad.apps.length - 1, i));
        const page = Math.floor(pad.selected / pad.perPage);
        if (page !== pages.currentIndex) {
            pages.currentIndex = page;
        }
    }
    function turn(step) {
        const page = Math.max(0, Math.min(pad.pageCount - 1, pages.currentIndex + step));
        if (page === pages.currentIndex) {
            return;
        }
        pages.currentIndex = page;
        if (pad.selected >= 0) {
            pad.selected = Math.min(pad.apps.length - 1, page * pad.perPage);
        }
    }
    function wheel(event) {
        const delta = Math.abs(event.angleDelta.x) > Math.abs(event.angleDelta.y) ? -event.angleDelta.x : -event.angleDelta.y;
        if (pad.wheelResting) {
            return;
        }
        pad.wheelSum += delta;
        if (Math.abs(pad.wheelSum) >= 120) {
            pad.turn(pad.wheelSum > 0 ? 1 : -1);
            pad.wheelSum = 0;
            pad.wheelResting = true;             // one page per flick of a touchpad
            wheelRest.restart();
        }
    }
    Timer {
        id: wheelRest
        interval: 380
        onTriggered: {
            pad.wheelResting = false;
            pad.wheelSum = 0;
        }
    }
    function key(event) {
        const at = pad.selected;
        const first = pages.currentIndex * pad.perPage;
        switch (event.key) {
        case Qt.Key_Escape:
            if (search.text.length > 0) {
                search.text = "";
            } else {
                dock.setLaunchpadOpen(false);
            }
            break;
        case Qt.Key_Return:
        case Qt.Key_Enter:
            if (at >= 0 && at < pad.apps.length) {
                pad.launch(pad.apps[at].appId);
            } else if (pad.runnerResults.length > 0) {
                pad.runResult(pad.runnerResults[0]);
            }
            break;
        case Qt.Key_Right:
            pad.select(at < 0 ? first : at + 1);
            break;
        case Qt.Key_Left:
            pad.select(at < 0 ? first : at - 1);
            break;
        case Qt.Key_Down:
            pad.select(at < 0 ? first : at + pad.columns);
            break;
        case Qt.Key_Up:
            pad.select(at < 0 ? first : at - pad.columns);
            break;
        case Qt.Key_PageDown:
            pad.turn(1);
            break;
        case Qt.Key_PageUp:
            pad.turn(-1);
            break;
        default:
            return;
        }
        event.accepted = true;
    }
    function openMenu(tile, appId) {
        const p = tile.mapToItem(null, tile.width / 2, tile.height * 0.55);
        menu.appId = appId;
        menu.entries = dock.launchpadMenu(appId);
        menu.currentIndex = -1;
        menu.anchorPoint = Qt.point(p.x, p.y);
        menu.visible = true;
        menu.forceActiveFocus();
    }
    function beginDrag() {
        pad.dragging = true;
        dock.launchpadDragging = true;
    }
    function endDrag() {
        dock.launchpadDragging = false;
        pad.dragging = false;
        dock.setLaunchpadOpen(false);
    }

    // one app: its icon and name
    component AppTile: Item {
        id: tile
        required property var modelData
        required property int index
        property int first: 0
        readonly property bool current: pad.selected === first + index

        width: pad.cellWidth
        height: pad.cellHeight

        Rectangle {
            anchors.horizontalCenter: parent.horizontalCenter
            y: glyph.y - pad.iconSize * 0.14
            width: pad.iconSize * 1.28
            height: width
            radius: width * 0.24
            color: Qt.rgba(Kirigami.Theme.textColor.r, Kirigami.Theme.textColor.g, Kirigami.Theme.textColor.b,
                           tile.current ? 0.2 : area.containsMouse ? 0.1 : 0)
            border.width: tile.current ? 1 : 0
            border.color: Kirigami.Theme.highlightColor
        }
        Kirigami.Icon {
            id: glyph
            anchors.horizontalCenter: parent.horizontalCenter
            y: pad.cellHeight * 0.1
            width: pad.iconSize
            height: width
            source: tile.modelData.icon
            roundToIconSize: false
            scale: area.pressed ? 0.9 : 1
            Behavior on scale {
                NumberAnimation { duration: 90 }
            }
        }
        Text {
            anchors.top: glyph.bottom
            anchors.topMargin: pad.iconSize * 0.16
            anchors.horizontalCenter: parent.horizontalCenter
            width: parent.width - 8
            horizontalAlignment: Text.AlignHCenter
            text: tile.modelData.name
            textFormat: Text.PlainText
            elide: Text.ElideRight
            color: Kirigami.Theme.textColor
            font.pointSize: Kirigami.Theme.defaultFont.pointSize
        }
        MouseArea {
            id: area
            anchors.fill: parent
            hoverEnabled: true
            preventStealing: true
            acceptedButtons: Qt.LeftButton | Qt.RightButton
            drag.target: carrier
            drag.threshold: 10
            // holding an app opens its menu too, for touchpads and touch screens
            pressAndHoldInterval: 600
            onPressAndHold: mouse => pad.openMenu(tile, tile.modelData.appId)
            onPressed: mouse => {
                if (mouse.button === Qt.LeftButton) {
                    glyph.grabToImage(result => {
                        carrier.picture = result;
                        carrier.Drag.imageSource = result.url;
                    }, Qt.size(pad.iconSize, pad.iconSize));
                }
            }
            onClicked: mouse => {
                if (mouse.button === Qt.RightButton) {
                    pad.openMenu(tile, tile.modelData.appId);
                } else {
                    pad.launch(tile.modelData.appId);
                }
            }
        }
        // what travels when the app is dragged to the dock
        Item {
            id: carrier
            property var picture: null
            width: pad.iconSize
            height: pad.iconSize
            Drag.active: area.drag.active
            Drag.dragType: Drag.Automatic
            Drag.supportedActions: Qt.CopyAction | Qt.LinkAction
            Drag.hotSpot.x: width / 2
            Drag.hotSpot.y: height / 2
            Drag.mimeData: ({ "text/uri-list": "applications:" + tile.modelData.appId + ".desktop\r\n" })
            Drag.onDragStarted: pad.beginDrag()
            Drag.onDragFinished: dropAction => {
                carrier.x = 0;
                carrier.y = 0;
                pad.endDrag();
            }
        }
    }

    Item {
        id: sheet
        anchors.fill: parent
        opacity: pad.open && !pad.dragging ? 1 : 0
        scale: pad.open ? 1 : 1.05
        Behavior on opacity {
            enabled: pad.anim > 0
            NumberAnimation { duration: 180 * pad.anim; easing.type: Easing.OutCubic }
        }
        Behavior on scale {
            enabled: pad.anim > 0
            NumberAnimation { duration: 220 * pad.anim; easing.type: Easing.OutCubic }
        }

        Kirigami.Theme.colorSet: Kirigami.Theme.Window
        Kirigami.Theme.inherit: false

        // a tint over the blurred desktop
        Rectangle {
            anchors.fill: parent
            color: Qt.rgba(Kirigami.Theme.backgroundColor.r, Kirigami.Theme.backgroundColor.g,
                           Kirigami.Theme.backgroundColor.b, 0.55)
        }

        // a click on the glass, not on an app, leaves (a right-click there is
        // more likely a look for a menu than a wish to leave, so it stays)
        MouseArea {
            anchors.fill: parent
            acceptedButtons: Qt.LeftButton
            onClicked: dock.setLaunchpadOpen(false)
        }
        WheelHandler {
            onWheel: event => pad.wheel(event)
        }

        Rectangle {
            id: searchBox
            width: Math.min(440, pad.width * 0.36)
            height: 44
            anchors.horizontalCenter: parent.horizontalCenter
            y: Math.round(pad.height * 0.07)
            radius: height / 2
            color: Qt.rgba(Kirigami.Theme.backgroundColor.r, Kirigami.Theme.backgroundColor.g,
                           Kirigami.Theme.backgroundColor.b, 0.7)
            border.width: 1
            border.color: Qt.rgba(Kirigami.Theme.textColor.r, Kirigami.Theme.textColor.g, Kirigami.Theme.textColor.b,
                                  search.activeFocus ? 0.32 : 0.16)

            Kirigami.Icon {
                id: searchIcon
                x: 16
                anchors.verticalCenter: parent.verticalCenter
                width: 18
                height: 18
                source: "search"
            }
            TextInput {
                id: search
                anchors.left: searchIcon.right
                anchors.leftMargin: 10
                anchors.right: parent.right
                anchors.rightMargin: 18
                anchors.verticalCenter: parent.verticalCenter
                color: Kirigami.Theme.textColor
                selectionColor: Kirigami.Theme.highlightColor
                selectedTextColor: Kirigami.Theme.highlightedTextColor
                font.pointSize: Kirigami.Theme.defaultFont.pointSize * 1.15
                clip: true
                focus: true
                Keys.onPressed: event => pad.key(event)
                onTextChanged: {
                    if (text.length > 0) {
                        pad.typed = true;
                    }
                    pad.grid.setQuery(text);
                    pages.currentIndex = 0;
                    pad.selected = text.length > 0 && pad.apps.length > 0 ? 0 : -1;
                    if (runners.item) {
                        runners.item.query = text;
                    }
                }
                Text {
                    anchors.fill: parent
                    verticalAlignment: Text.AlignVCenter
                    visible: search.text.length === 0 && search.preeditText.length === 0
                    text: qsTr("Search")
                    color: Kirigami.Theme.disabledTextColor
                    font: search.font
                }
            }
        }

        ListView {
            id: pages
            y: pad.gridTop
            width: parent.width
            height: pad.rows * pad.cellHeight
            orientation: ListView.Horizontal
            snapMode: ListView.SnapOneItem
            highlightRangeMode: ListView.StrictlyEnforceRange
            highlightMoveDuration: 280 * Math.max(0.2, pad.anim)
            boundsBehavior: Flickable.StopAtBounds
            cacheBuffer: width
            model: pad.pageCount

            WheelHandler {
                onWheel: event => pad.wheel(event)
            }

            delegate: Item {
                id: page
                required property int index
                width: pages.width
                height: pages.height

                MouseArea {
                    anchors.fill: parent
                    onClicked: dock.setLaunchpadOpen(false)
                }
                Grid {
                    anchors.horizontalCenter: parent.horizontalCenter
                    columns: pad.columns
                    Repeater {
                        model: pad.apps.slice(page.index * pad.perPage, (page.index + 1) * pad.perPage)
                        delegate: AppTile {
                            first: page.index * pad.perPage
                        }
                    }
                }
            }
        }

        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            y: pad.gridTop + pad.cellHeight
            visible: search.text.length > 0 && pad.apps.length === 0 && pad.runnerResults.length === 0
            text: qsTr("No apps match “%1”").arg(search.text)
            textFormat: Text.PlainText
            color: Kirigami.Theme.disabledTextColor
            font.pointSize: Kirigami.Theme.defaultFont.pointSize * 1.2
        }

        // what Plasma's runners found: settings pages, sums, conversions, files
        Row {
            id: runnerRow
            anchors.horizontalCenter: parent.horizontalCenter
            y: pages.y + pages.height + 18
            spacing: 10
            visible: pad.runnerResults.length > 0
            Repeater {
                model: pad.runnerResults
                delegate: Rectangle {
                    id: chip
                    required property var modelData
                    required property int index
                    readonly property bool preferred: index === 0 && pad.apps.length === 0
                    height: 48
                    width: Math.min(340, chipContent.implicitWidth + 32)
                    radius: 24
                    color: chipArea.containsMouse || preferred
                        ? Qt.rgba(Kirigami.Theme.highlightColor.r, Kirigami.Theme.highlightColor.g,
                                  Kirigami.Theme.highlightColor.b, 0.35)
                        : Qt.rgba(Kirigami.Theme.backgroundColor.r, Kirigami.Theme.backgroundColor.g,
                                  Kirigami.Theme.backgroundColor.b, 0.7)
                    border.width: 1
                    border.color: Qt.rgba(Kirigami.Theme.textColor.r, Kirigami.Theme.textColor.g,
                                          Kirigami.Theme.textColor.b, 0.16)
                    Row {
                        id: chipContent
                        anchors.centerIn: parent
                        spacing: 10
                        Kirigami.Icon {
                            anchors.verticalCenter: parent.verticalCenter
                            width: 24
                            height: 24
                            source: chip.modelData.icon
                        }
                        Column {
                            anchors.verticalCenter: parent.verticalCenter
                            Text {
                                width: Math.min(implicitWidth, 260)
                                text: chip.modelData.text
                                textFormat: Text.PlainText
                                elide: Text.ElideRight
                                color: Kirigami.Theme.textColor
                                font.pointSize: Kirigami.Theme.defaultFont.pointSize
                            }
                            Text {
                                width: Math.min(implicitWidth, 260)
                                text: chip.modelData.subtext || chip.modelData.groupName
                                textFormat: Text.PlainText
                                elide: Text.ElideRight
                                color: Kirigami.Theme.disabledTextColor
                                font.pointSize: Kirigami.Theme.smallFont.pointSize
                            }
                        }
                    }
                    MouseArea {
                        id: chipArea
                        anchors.fill: parent
                        hoverEnabled: true
                        onClicked: pad.runResult(chip.modelData)
                    }
                }
            }
        }

        Row {
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.bottom: parent.bottom
            anchors.bottomMargin: 40
            spacing: 12
            visible: pad.pageCount > 1
            Repeater {
                model: pad.pageCount
                Rectangle {
                    required property int index
                    width: 9
                    height: 9
                    radius: 4.5
                    color: Kirigami.Theme.textColor
                    opacity: index === pages.currentIndex ? 0.9 : 0.3
                    MouseArea {
                        anchors.fill: parent
                        anchors.margins: -6
                        onClicked: pages.currentIndex = parent.index
                    }
                }
            }
        }
    }

    Loader {
        id: runners
        active: pad.visible && pad.typed
        source: "LaunchpadRunners.qml"
        onLoaded: item.query = search.text
    }

    // a right-click menu for an app; a click elsewhere closes it
    MouseArea {
        anchors.fill: parent
        visible: menu.visible
        z: 19
        acceptedButtons: Qt.AllButtons
        onPressed: {
            menu.visible = false;
            search.forceActiveFocus();
        }
    }
    DockMenu {
        id: menu
        property string appId: ""
        property point anchorPoint: Qt.point(0, 0)
        visible: false
        z: 20
        x: Math.max(8, Math.min(pad.width - width - 8, anchorPoint.x - width / 2))
        y: Math.max(8, Math.min(pad.height - height - 8, anchorPoint.y))
        onTriggered: key => {
            menu.visible = false;
            dock.launchpadMenuTriggered(menu.appId, key);
            search.forceActiveFocus();
        }
        onDismissed: {
            menu.visible = false;
            search.forceActiveFocus();
        }
    }

    Rectangle {
        width: 1
        height: 1
        color: pad.commitTick % 2 ? "#01000000" : "#02000000"
    }
}
