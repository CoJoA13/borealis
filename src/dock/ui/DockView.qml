/*
    The dock itself, laid out as a bottom dock; for the side edges the content
    is rotated. Magnification is the integral of a cosine bump centred on the
    pointer, so sizes and positions both come from resting coordinates: nothing
    that moves feeds back into what is measured, and whatever sits under the
    pointer stays under it while its neighbours make room.
    SPDX-License-Identifier: GPL-3.0-or-later
*/
import QtQuick
import org.kde.kirigami as Kirigami

Item {
    id: view

    required property var window

    readonly property var cfg: dock.settings.values
    readonly property string edge: cfg.position
    readonly property bool vertical: edge !== "bottom"
    readonly property real anim: cfg.animation
    readonly property bool motion: anim > 0 && Kirigami.Units.longDuration > 1

    readonly property int iconSize: cfg.iconSize
    readonly property int padding: cfg.padding
    readonly property int thickness: iconSize + 2 * padding
    readonly property int dividerSpan: dock.model.dividerSpan
    readonly property var offsets: dock.model.restOffsets
    readonly property real restLength: dock.model.restLength
    readonly property real restStart: Math.round((content.width - restLength) / 2)
    readonly property real restEnd: restStart + restLength
    readonly property real shelfY: content.height - cfg.margin - thickness

    // ---- magnification ----------------------------------------------------
    property real pointer: dock.pointerOverride
    property real focusAt: dock.pointerOverride
    onPointerChanged: if (pointer >= 0) {
        focusAt = pointer;
    }
    property real swell: pointer >= 0 && cfg.zoom > 1 ? 1 : 0
    Behavior on swell {
        enabled: view.motion
        NumberAnimation { duration: 200 * view.anim; easing.type: Easing.OutCubic }
    }
    readonly property real zoom: 1 + (cfg.zoom - 1) * swell
    readonly property real reach: Math.max(1, iconSize * cfg.reach)

    function live(x) {
        if (focusAt < 0 || zoom <= 1.0001) {
            return x;
        }
        const d = x - focusAt;
        const a = Math.min(Math.abs(d), reach);
        return focusAt + d + Math.sign(d) * (zoom - 1) / 2 * (a + reach / Math.PI * Math.sin(Math.PI * a / reach));
    }
    readonly property real liveStart: live(restStart)
    readonly property real liveEnd: live(restEnd)

    // ---- hiding -------------------------------------------------------------
    readonly property string screenName: window.screen ? window.screen.name : ""
    readonly property bool hoveredDock: hover.hovered || edgeHover.hovered || dropArea.containsDrag
        || dock.pointerOverride >= 0
    property bool dragging: false
    property bool covered: false
    property bool autoHidden: false
    property bool revealHold: false
    readonly property bool fullscreenHere: dock.windowsRevision >= 0 && dock.fullscreenOn(screenName)
    readonly property bool hidden: !hoveredDock && !dragging && !dock.menuOpen && !revealHold
        && (fullscreenHere || (cfg.hide === "dodge" && covered) || (cfg.hide === "auto" && autoHidden))

    Timer {
        id: coverTimer
        interval: 150
        onTriggered: view.covered = view.checkCovered()
    }
    Timer {
        id: autoTimer
        interval: Math.max(1, view.cfg.hideDelay)
        onTriggered: view.autoHidden = true
    }
    Timer {
        id: holdTimer
        interval: 700
        onTriggered: view.revealHold = false
    }
    Connections {
        target: dock
        function onWindowsRevisionChanged() {
            coverTimer.restart();
        }
        function onTestMenuRequested(row) {
            const it = repeater.itemAt(row);
            if (it) {
                view.openMenu(it);
            }
        }
    }
    onRestLengthChanged: coverTimer.restart()
    onHoveredDockChanged: {
        if (hoveredDock) {
            autoTimer.stop();
            autoHidden = false;
        } else if (cfg.hide === "auto") {
            autoTimer.restart();
        }
        Qt.callLater(pushSurface);
    }
    onLiveStartChanged: Qt.callLater(pushSurface)
    onLiveEndChanged: Qt.callLater(pushSurface)
    onHiddenChanged: Qt.callLater(pushSurface)
    onDraggingChanged: Qt.callLater(pushSurface)
    onWidthChanged: Qt.callLater(pushSurface)
    onHeightChanged: Qt.callLater(pushSurface)
    onCfgChanged: {
        coverTimer.restart();
        if (cfg.hide !== "auto") {
            autoTimer.stop();
            autoHidden = false;
        } else if (!hoveredDock && !autoHidden) {
            autoTimer.restart();        // switched on while the pointer was elsewhere
        }
        Qt.callLater(pushSurface);
    }
    Component.onCompleted: {
        if (cfg.hide === "auto") {
            autoTimer.restart();
        }
        coverTimer.restart();
        Qt.callLater(pushSurface);
    }

    // content coordinates -> surface coordinates (ignoring the slide)
    function toView(x, y, w, h) {
        if (edge === "left") {
            return Qt.rect(content.height - y - h, x, h, w);
        }
        if (edge === "right") {
            return Qt.rect(y, content.width - x - w, h, w);
        }
        return Qt.rect(x, y, w, h);
    }

    // where this surface's top-left corner sits on the whole desktop
    // (QML's window.screen has no geometry; Python asks the real QScreen)
    function screenOrigin() {
        const g = dock.screenRect(window);
        return Qt.point(g.x + (edge === "right" ? g.width - window.width : 0),
                        g.y + (edge === "bottom" ? g.height - window.height : 0));
    }

    function checkCovered() {
        if (restLength <= 0) {
            return false;
        }
        const r = toView(restStart - padding, shelfY, restLength + 2 * padding, thickness + cfg.margin);
        const o = screenOrigin();
        return dock.overlaps(screenName, o.x + r.x, o.y + r.y, r.width, r.height);
    }

    // input region and blur for the compositor
    function pushSurface() {
        const s = content.slide;
        const gone = hidden && s >= content.height - 1;
        const mask = [];
        if (!gone) {
            if (hoveredDock || dragging) {
                mask.push(toView(liveStart - padding, s, liveEnd - liveStart + 2 * padding, content.height));
            } else {
                mask.push(toView(restStart - padding, shelfY + s, restLength + 2 * padding, content.height - shelfY));
            }
        }
        if (hidden) {
            mask.push(Qt.rect(edgeStrip.x, edgeStrip.y, edgeStrip.width, edgeStrip.height));
        }
        const blur = cfg.blur && !gone && restLength > 0
            ? toView(liveStart - padding, shelfY + s, liveEnd - liveStart + 2 * padding, thickness)
            : Qt.rect(0, 0, 0, 0);
        dock.updateSurface(window, mask, blur, shelf.radius);
    }

    function rowAt(x) {
        for (let i = 0; i < repeater.count; i++) {
            const it = repeater.itemAt(i);
            if (it && x >= it.liveA - cfg.spacing / 2 && x < it.liveB + cfg.spacing / 2) {
                return i;
            }
        }
        return -1;
    }

    function openMenu(it) {
        const r = it ? it.mapToItem(null, 0, 0, it.width, it.height)
                     : shelf.mapToItem(null, 0, 0, shelf.width, shelf.height);
        const g = dock.screenRect(window);
        const o = screenOrigin();
        dock.requestMenu(it ? it.index : -1, window, o.x - g.x + r.x, o.y - g.y + r.y, r.width, r.height, edge);
    }

    function openStack(it) {
        const r = it.mapToItem(null, 0, 0, it.width, it.height);
        const g = dock.screenRect(window);
        const o = screenOrigin();
        dock.requestStack(it.index, window, o.x - g.x + r.x, o.y - g.y + r.y, r.width, r.height, edge);
    }

    // ---- dragging icons -----------------------------------------------------
    property int dragRow: -1
    property real dragX: 0
    property real dragY: 0
    readonly property bool removing: dragging && shelfY - dragY > thickness + iconSize * 0.5

    function beginDrag(it) {
        dragRow = it.index;
        dragging = true;
    }
    function moveDrag(it, scenePos) {
        const p = content.mapFromItem(null, scenePos.x, scenePos.y);
        dragX = p.x;
        dragY = p.y;
        pointer = p.x;
        if (removing) {
            return;
        }
        let target = -1;
        let best = Infinity;
        for (let i = 0; i < repeater.count; i++) {
            const c = repeater.itemAt(i);
            if (!c || c.kind !== "app" || !c.pinned || i === dragRow) {
                continue;
            }
            const d = Math.abs((c.liveA + c.liveB) / 2 - p.x);
            if (d < best) {
                best = d;
                target = i;
            }
        }
        if (target >= 0 && best < iconSize * 0.6) {
            dragRow = dock.moveItem(dragRow, target);
        }
    }
    function endDrag(it) {
        if (removing && it.pinned) {
            dock.unpin(dragRow);
        } else {
            dock.commitOrder();
        }
        dragging = false;
        dragRow = -1;
        pointer = hover.hovered ? pointer : dock.pointerOverride;
    }

    // ---- what you see -------------------------------------------------------
    Item {
        id: content
        width: view.vertical ? view.height : view.width
        height: view.vertical ? view.width : view.height
        anchors.centerIn: parent
        rotation: view.edge === "left" ? 90 : view.edge === "right" ? -90 : 0

        property real slide: view.hidden ? height : 0
        Behavior on slide {
            enabled: view.motion
            NumberAnimation { duration: 280 * view.anim; easing.type: Easing.InOutCubic }
        }
        onSlideChanged: Qt.callLater(view.pushSurface)
        transform: Translate { y: content.slide }

        Rectangle {
            id: shelf
            Kirigami.Theme.colorSet: Kirigami.Theme.Window
            Kirigami.Theme.inherit: false
            visible: view.restLength > 0
            x: view.liveStart - view.padding
            y: view.shelfY
            width: view.liveEnd - view.liveStart + 2 * view.padding
            height: view.thickness
            radius: Math.min(view.cfg.radius, height / 2)
            color: Qt.rgba(Kirigami.Theme.backgroundColor.r, Kirigami.Theme.backgroundColor.g,
                           Kirigami.Theme.backgroundColor.b, view.cfg.opacity)
            border.width: view.cfg.border ? 1 : 0
            border.color: Qt.rgba(Kirigami.Theme.textColor.r, Kirigami.Theme.textColor.g,
                                  Kirigami.Theme.textColor.b, 0.14)

            TapHandler {
                acceptedButtons: Qt.RightButton
                onTapped: view.openMenu(null)
            }
        }

        // Pointer tracking for the swell: a passive handler, so the icons'
        // own tap and drag handlers still get every event. At rest it covers
        // the shelf down to the screen edge; while hovered, the whole swell.
        Item {
            id: hoverZone
            readonly property bool wide: view.hoveredDock || view.dragging
            x: (wide ? view.liveStart : view.restStart) - view.padding
            y: wide ? 0 : view.shelfY
            width: (wide ? view.liveEnd - view.liveStart : view.restLength) + 2 * view.padding
            height: content.height - y

            HoverHandler {
                id: hover
                onPointChanged: if (hovered) {
                    view.pointer = point.position.x + hoverZone.x;
                }
                onHoveredChanged: if (!hovered && !view.dragging) {
                    view.pointer = dock.pointerOverride;
                }
            }
        }

        Repeater {
            id: repeater
            model: dock.model
            delegate: DockItem {
                host: view
            }
        }

        DropArea {
            id: dropArea
            x: view.restStart - view.padding - view.iconSize
            y: view.shelfY - view.iconSize
            width: view.restLength + 2 * (view.padding + view.iconSize)
            height: content.height - y
            onPositionChanged: drag => view.pointer = drag.x + x
            onExited: view.pointer = dock.pointerOverride
            onDropped: drop => {
                if (drop.hasUrls) {
                    dock.dropUrls(view.rowAt(drop.x + x), drop.urls);
                    drop.acceptProposedAction();
                }
                view.pointer = dock.pointerOverride;
            }
        }
    }

    // While hidden, a thin strip along the screen edge brings the dock back
    Item {
        id: edgeStrip
        readonly property rect area: view.toView(view.restStart - view.padding - view.iconSize, content.height - 2,
                                                  view.restLength + 2 * (view.padding + view.iconSize), 2)
        enabled: view.hidden
        x: area.x
        y: area.y
        width: area.width
        height: area.height

        HoverHandler {
            id: edgeHover
            onHoveredChanged: if (hovered) {
                view.revealHold = true;
                holdTimer.restart();
            }
        }
    }
}
