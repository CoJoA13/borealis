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

    readonly property string version: "1"
    readonly property string service: "org.borealis.Dock"
    readonly property string objectPath: "/Dock"
    readonly property string iface: "org.borealis.Dock1"
    readonly property string shortcutName: "Borealis Dock: sync"
    property bool debug: false          // the dock turns this on when it runs with tracing

    function listed(w) {
        return w.normalWindow === true && w.skipTaskbar !== true;
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

    function watch(w) {
        const signals = ["minimizedChanged", "captionChanged", "frameGeometryChanged", "activeChanged",
                         "demandsAttentionChanged", "desktopsChanged", "outputChanged",
                         "fullScreenChanged", "skipTaskbarChanged", "desktopFileNameChanged"];
        for (let i = 0; i < signals.length; i++) {
            const name = signals[i];
            if (w[name]) {
                w[name].connect(() => {
                    if (bridge.debug && name !== "frameGeometryChanged") {
                        bridge.say(name + ": " + w.caption + " skipTaskbar=" + w.skipTaskbar + " app=" + w.desktopFileName);
                    }
                    throttle.poke();
                });
            } else if (bridge.debug) {
                bridge.say("no signal " + name);
            }
        }
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
