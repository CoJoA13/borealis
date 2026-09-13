/*
    A bar menu with its submenus: up to five levels side by side, opened by
    hovering or with the arrow keys. Submenus the app fills in lazily arrive
    through fill() once the app has answered.
    SPDX-License-Identifier: GPL-3.0-or-later
*/
import QtQuick

Item {
    id: root

    property var entries: []
    property real maxRight: 1e9
    property int depth: 1
    // each level's entries, parent key and place (separate properties, so
    // changing one level doesn't rebuild the others)
    property var level0: []
    property var level1: []
    property var level2: []
    property var level3: []
    property var level4: []
    property var parents: ["", "", "", "", ""]
    property var places: [Qt.point(0, 0), Qt.point(0, 0), Qt.point(0, 0), Qt.point(0, 0), Qt.point(0, 0)]
    readonly property var first: panels.itemAt(0)
    signal triggered(string key)
    signal submenuWanted(string key)
    signal dismissed()

    width: first ? first.width : 0
    height: first ? first.height : 0
    focus: true

    function levelEntries(i) {
        return i === 0 ? level0 : i === 1 ? level1 : i === 2 ? level2 : i === 3 ? level3 : level4;
    }
    function setLevel(i, value) {
        if (i === 0) level0 = value;
        else if (i === 1) level1 = value;
        else if (i === 2) level2 = value;
        else if (i === 3) level3 = value;
        else if (i === 4) level4 = value;
    }
    function reset() {
        depth = 1;
        level0 = root.entries;
        const panel = panels.itemAt(0);
        if (panel) {
            panel.currentIndex = -1;
        }
    }
    function closeFrom(i) {
        depth = Math.max(1, Math.min(depth, i));
    }
    function openSubmenu(from, entry, rowY) {
        if (from >= 4) {
            return;
        }
        const panel = panels.itemAt(from);
        let x = panel.x + panel.width - 4;
        if (root.x + x + 260 > root.maxRight) {
            x = panel.x - 256;
        }
        const parents = root.parents.slice();
        parents[from + 1] = entry.key;
        const places = root.places.slice();
        places[from + 1] = Qt.point(x, panel.y + rowY - 6);
        root.parents = parents;
        root.places = places;
        setLevel(from + 1, entry.children || []);
        depth = from + 2;
        const child = panels.itemAt(from + 1);
        if (child) {
            child.currentIndex = -1;
        }
        root.submenuWanted(entry.key);
    }
    function fill(key, entries) {
        for (let i = 1; i < depth; i++) {
            if (parents[i] === key) {
                setLevel(i, entries);
            }
        }
    }
    function keyPanel() {
        return panels.itemAt(depth - 1);
    }

    Keys.onUpPressed: keyPanel().step(-1)
    Keys.onDownPressed: keyPanel().step(1)
    Keys.onReturnPressed: keyPanel().activateCurrent()
    Keys.onEnterPressed: keyPanel().activateCurrent()
    Keys.onRightPressed: {
        const panel = keyPanel();
        const entry = panel.entries[panel.currentIndex];
        if (entry && entry.type === "submenu") {
            openSubmenu(depth - 1, entry, panel.rowY(panel.currentIndex));
            keyPanel().step(1);
        }
    }
    Keys.onLeftPressed: closeFrom(depth - 1)
    Keys.onEscapePressed: depth > 1 ? closeFrom(depth - 1) : dismissed()

    Timer {
        id: hoverOpen
        property int from: 0
        property var entry: null
        property real rowY: 0
        interval: 160
        onTriggered: {
            if (entry && entry.type === "submenu") {
                root.openSubmenu(from, entry, rowY);
            } else {
                root.closeFrom(from + 1);
            }
        }
    }

    Repeater {
        id: panels
        model: 5
        delegate: MenuPanel {
            required property int index
            visible: index < root.depth
            x: root.places[index].x
            y: root.places[index].y
            entries: root.levelEntries(index)
            opacityLevel: index === 0 ? 0.9 : 0.97
            onActivated: (entry, rowY) => {
                if (entry.type === "submenu") {
                    root.openSubmenu(index, entry, rowY);
                } else {
                    root.triggered(entry.key);
                }
            }
            onHovered: (entry, rowY) => {
                if (root.depth > index + 1 && root.parents[index + 1] === entry.key) {
                    hoverOpen.stop();
                    return;
                }
                hoverOpen.from = index;
                hoverOpen.entry = entry;
                hoverOpen.rowY = rowY;
                hoverOpen.restart();
            }
        }
    }
}
