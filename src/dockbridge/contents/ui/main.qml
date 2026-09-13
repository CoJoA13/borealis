/*
    Borealis Dock bridge. KWin keeps its window list to itself (only
    plasmashell may ask), so this script reports the windows to the dock over
    D-Bus and carries out the dock's window commands. The dock queues commands
    and pokes the "sync" shortcut; the script then collects them.
    Small on purpose: it runs inside the compositor.
    SPDX-License-Identifier: GPL-3.0-or-later
*/
import QtQuick
import org.kde.kwin as KWin

Item {
    id: bridge

    readonly property string version: "2"
    readonly property string service: "org.borealis.Dock"
    readonly property string objectPath: "/Dock"
    readonly property string iface: "org.borealis.Dock1"
    readonly property string shortcutName: "Borealis Dock: sync"
    readonly property string slotShortcut: "Borealis Dock: activate app "
    readonly property string launchpadShortcut: "Borealis Dock: Launchpad"
    property bool shortcutsEnabled: false   // Meta+1…9, when the dock asks for them
    property bool debug: false          // the dock turns this on when it runs with tracing

    function listed(w) {
        // KWin's own windows (these previews, on-screen displays) have no process
        return w.normalWindow === true && w.skipTaskbar !== true && w.popupWindow !== true && w.pid !== -1;
    }

    // ---- previews ---------------------------------------------------------
    function outputRect(name) {
        const screens = KWin.Workspace.screens;
        for (let i = 0; i < screens.length; i++) {
            const g = screens[i].geometry;
            if (screens[i].name === name && g && g.width > 0) {
                return Qt.rect(g.x, g.y, g.width, g.height);
            }
        }
        return Qt.rect(0, 0, 0, 0);
    }

    function showPreview(c) {
        const p = previewLoader.item;
        if (!p) {
            return;
        }
        const entries = [];
        const ids = c.ids || [];
        for (let i = 0; i < ids.length; i++) {
            const w = bridge.find(ids[i]);
            if (w) {
                entries.push({ window: w, id: w.internalId });
            }
        }
        if (entries.length === 0) {
            bridge.hidePreview();
            return;
        }
        closeTimer.stop();
        p.edge = c.edge || "bottom";
        p.anchorRect = Qt.rect(c.x, c.y, c.w, c.h);
        p.area = bridge.outputRect(c.output || "");
        p.entries = entries;
        p.visible = true;
        p.place();
        Qt.callLater(() => { if (previewLoader.item) previewLoader.item.place(); });
        bridge.reportPreview();
    }

    function hidePreview() {
        closeTimer.stop();
        if (previewLoader.item && previewLoader.item.visible) {
            previewLoader.item.visible = false;
            previewLoader.item.entries = [];
        }
        bridge.reportPreview();
    }

    property bool reportedVisible: false
    property bool reportedHovered: false
    function reportPreview() {
        const p = previewLoader.item;
        const shown = !!p && p.visible;
        const hovered = shown && p.hovered;
        if (shown === reportedVisible && hovered === reportedHovered) {
            return;
        }
        reportedVisible = shown;
        reportedHovered = hovered;
        previewState.arguments = [shown, hovered];
        previewState.call();
    }

    function describe(w, index, current) {
        const g = w.frameGeometry;
        const desktops = w.desktops || [];
        return {
            id: String(w.internalId),
            app: String(w.desktopFileName || ""),
            cls: String(w.resourceClass || ""),
            name: String(w.resourceName || ""),
            caption: String(w.caption || ""),
            active: w.active === true,
            minimized: w.minimized === true,
            attention: w.demandsAttention === true,
            fullScreen: w.fullScreen === true,
            output: w.output ? String(w.output.name) : "",
            here: w.onAllDesktops === true || desktops.length === 0 || desktops.indexOf(current) >= 0,
            stack: index,
            geometry: [Math.round(g.x), Math.round(g.y), Math.round(g.width), Math.round(g.height)]
        };
    }

    function snapshot() {
        const list = KWin.Workspace.stackingOrder;
        const current = KWin.Workspace.currentDesktop;
        const out = [];
        for (let i = 0; i < list.length; i++) {
            if (listed(list[i])) {
                out.push(describe(list[i], i, current));
            }
        }
        return JSON.stringify({ version: version, windows: out });
    }

    function find(id) {
        const list = KWin.Workspace.stackingOrder;
        for (let i = 0; i < list.length; i++) {
            if (String(list[i].internalId) === id) {
                return list[i];
            }
        }
        return null;
    }

    function run(commands) {
        for (let i = 0; i < commands.length; i++) {
            const c = commands[i];
            if (c.op === "resync") {
                bridge.pushNow();
                continue;
            }
            if (c.op === "config") {
                if (c.shortcuts !== undefined) {
                    bridge.shortcutsEnabled = c.shortcuts === true;
                }
                continue;
            }
            if (c.op === "debug") {
                bridge.debug = c.on === true;
                continue;
            }
            if (c.op === "dump") {
                const list = KWin.Workspace.stackingOrder;
                for (let j = 0; j < list.length; j++) {
                    const x = list[j];
                    bridge.say("dump " + j + ": caption='" + x.caption + "' app='" + x.desktopFileName + "' class='"
                               + x.resourceClass + "' type=" + x.windowType + " normal=" + x.normalWindow
                               + " dialog=" + x.dialog + " transient=" + x.transient + " skipTaskbar=" + x.skipTaskbar
                               + " skipSwitcher=" + x.skipSwitcher + " hidden=" + x.hidden + " minimized=" + x.minimized
                               + " fullScreen=" + x.fullScreen + " keepAbove=" + x.keepAbove + " active=" + x.active
                               + " managed=" + x.managed + " deleted=" + x.deleted + " popup=" + x.popupWindow
                               + " geometry=" + x.frameGeometry);
                }
                continue;
            }
            if (c.op === "preview") {
                bridge.showPreview(c);
                continue;
            }
            if (c.op === "previewLeave") {
                // the pointer may be on its way to the previews: wait a moment
                // (and a preview asked for in the same breath closes too, unless it's reached)
                closeTimer.restart();
                continue;
            }
            if (c.op === "previewHide") {
                bridge.hidePreview();
                continue;
            }
            const w = c.id ? find(c.id) : null;
            if (!w) {
                continue;
            }
            if (c.op === "activate") {
                w.minimized = false;
                KWin.Workspace.activeWindow = w;
            } else if (c.op === "minimize") {
                w.minimized = true;
            } else if (c.op === "close") {
                w.closeWindow();
            }
        }
    }

    // Connections to the windows' own signals. The windows outlive this
    // script when it's unloaded (an update, the dock turned off), and a
    // function still connected would keep firing into a script that's gone;
    // so each is remembered and disconnected again.
    property var hooks: []

    function watch(w) {
        const signals = ["minimizedChanged", "captionChanged", "frameGeometryChanged", "activeChanged",
                         "demandsAttentionChanged", "desktopsChanged", "outputChanged",
                         "fullScreenChanged", "skipTaskbarChanged", "desktopFileNameChanged"];
        for (let i = 0; i < signals.length; i++) {
            const name = signals[i];
            if (!w[name]) {
                if (bridge.debug) {
                    bridge.say("no signal " + name);
                }
                continue;
            }
            const hook = () => {
                if (!bridge || !throttle) {
                    return;             // the script was unloaded under us
                }
                if (bridge.debug && name !== "frameGeometryChanged") {
                    bridge.say(name + ": " + w.caption + " skipTaskbar=" + w.skipTaskbar + " app=" + w.desktopFileName);
                }
                throttle.poke();
            };
            w[name].connect(hook);
            bridge.hooks.push({ window: w, name: name, hook: hook });
        }
    }

    function unwatch(w) {
        bridge.hooks = bridge.hooks.filter(h => {
            if (h.window !== w) {
                return true;
            }
            try {
                h.window[h.name].disconnect(h.hook);
            } catch (e) {
                // the window is already gone, and its connections with it
            }
            return false;
        });
    }

    Component.onDestruction: {
        for (let i = 0; i < bridge.hooks.length; i++) {
            const h = bridge.hooks[i];
            try {
                h.window[h.name].disconnect(h.hook);
            } catch (e) {
                // already gone
            }
        }
        bridge.hooks = [];
    }

    property string lastSnapshot: ""

    function pushNow() {
        try {
            const snap = bridge.snapshot();
            if (bridge.debug) {
                bridge.say("push, windows in stacking order: " + KWin.Workspace.stackingOrder.length);
            }
            bridge.lastSnapshot = snap;
            push.arguments = [snap];
            push.call();
        } catch (e) {
            bridge.say("snapshot failed: " + e);
        }
    }

    function say(text) {
        logCall.arguments = [String(text)];
        logCall.call();
    }

    // A safety net: some changes arrive without a signal we can hear (an app
    // setting its id after mapping, say). A snapshot is cheap; send it only
    // when it differs from the last one.
    Timer {
        interval: 1500
        repeat: true
        running: true
        onTriggered: {
            try {
                if (bridge.snapshot() !== bridge.lastSnapshot) {
                    bridge.pushNow();
                }
            } catch (e) {
                bridge.say("snapshot failed: " + e);
            }
        }
    }

    // at most one snapshot per interval, however busy the windows get
    Timer {
        id: throttle
        interval: 60
        function poke() {
            if (!running) {
                start();
            }
        }
        onTriggered: bridge.pushNow()
    }

    KWin.DBusCall {
        id: push
        service: bridge.service
        path: bridge.objectPath
        dbusInterface: bridge.iface
        method: "WindowsChanged"
    }

    KWin.DBusCall {
        id: take
        service: bridge.service
        path: bridge.objectPath
        dbusInterface: bridge.iface
        method: "TakeCommands"
        onFinished: returnValue => {
            try {
                bridge.run(JSON.parse(returnValue[0]));
            } catch (e) {
                bridge.say("commands failed: " + e);
            }
        }
    }

    KWin.DBusCall {
        id: logCall
        service: bridge.service
        path: bridge.objectPath
        dbusInterface: bridge.iface
        method: "Log"
    }

    KWin.DBusCall {
        id: hello
        service: bridge.service
        path: bridge.objectPath
        dbusInterface: bridge.iface
        method: "Hello"
    }

    // Meta+1…9 open the dock's first nine apps (created only while wanted, so
    // the keys stay free otherwise)
    Instantiator {
        model: bridge.shortcutsEnabled ? 9 : 0
        delegate: KWin.ShortcutHandler {
            required property int index
            name: bridge.slotShortcut + (index + 1)
            text: bridge.slotShortcut + (index + 1)
            sequence: "Meta+" + (index + 1)
            onActivated: {
                slotCall.arguments = [index + 1];
                slotCall.call();
            }
        }
    }

    KWin.DBusCall {
        id: slotCall
        service: bridge.service
        path: bridge.objectPath
        dbusInterface: bridge.iface
        method: "ActivateSlot"
    }

    // Launchpad, from anywhere
    KWin.ShortcutHandler {
        name: bridge.launchpadShortcut
        text: bridge.launchpadShortcut
        sequence: "Meta+Space"
        onActivated: {
            // on the screen being worked on
            launchpadCall.arguments = [KWin.Workspace.activeScreen ? String(KWin.Workspace.activeScreen.name) : ""];
            launchpadCall.call();
        }
    }

    KWin.DBusCall {
        id: launchpadCall
        service: bridge.service
        path: bridge.objectPath
        dbusInterface: bridge.iface
        method: "ToggleLaunchpadOn"
    }

    KWin.DBusCall {
        id: previewState
        service: bridge.service
        path: bridge.objectPath
        dbusInterface: bridge.iface
        method: "PreviewState"
    }

    Loader {
        id: previewLoader
        source: "Previews.qml"
        onStatusChanged: if (status === Loader.Error) {
            bridge.say("window previews couldn't load");
        }
    }

    Connections {
        target: previewLoader.item
        function onHoveredChanged() {
            if (previewLoader.item.hovered) {
                closeTimer.stop();
            } else if (previewLoader.item.visible) {
                closeTimer.restart();
            }
            bridge.reportPreview();
        }
        function onVisibleChanged() {
            bridge.reportPreview();
        }
        function onActivateRequested(w) {
            if (w) {
                w.minimized = false;
                KWin.Workspace.activeWindow = w;
            }
            bridge.hidePreview();
        }
        function onCloseRequested(w) {
            if (w) {
                w.closeWindow();
            }
        }
    }

    Timer {
        id: closeTimer
        interval: 300
        onTriggered: if (!(previewLoader.item && previewLoader.item.hovered)) {
            bridge.hidePreview();
        }
    }

    KWin.ShortcutHandler {
        name: bridge.shortcutName
        text: bridge.shortcutName
        onActivated: take.call()
    }

    Connections {
        target: KWin.Workspace
        function onWindowAdded(w) {
            if (bridge.debug) {
                bridge.say("added " + w.caption + " app=" + w.desktopFileName + " class=" + w.resourceClass
                           + " normal=" + w.normalWindow + " skipTaskbar=" + w.skipTaskbar);
            }
            bridge.watch(w);
            throttle.poke();
        }
        function onWindowRemoved(w) {
            bridge.unwatch(w);
            const p = previewLoader.item;
            if (p && p.visible) {
                const left = p.entries.filter(e => String(e.id) !== String(w.internalId));
                if (left.length === 0) {
                    bridge.hidePreview();
                } else if (left.length !== p.entries.length) {
                    p.entries = left;
                }
            }
            throttle.poke();
        }
        function onWindowActivated(w) {
            throttle.poke();
        }
        function onCurrentDesktopChanged() {
            throttle.poke();
        }
    }

    Component.onCompleted: {
        const list = KWin.Workspace.stackingOrder;
        for (let i = 0; i < list.length; i++) {
            bridge.watch(list[i]);
        }
        hello.arguments = [bridge.version];
        hello.call();
        bridge.pushNow();
    }
}
