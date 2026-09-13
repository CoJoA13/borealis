/*
    Borealis Tweaks — one place for the whole Borealis desktop: the theme and
    its palette, the dock, and everything beyond Plasma, with undo.
    SPDX-License-Identifier: GPL-3.0-or-later
*/

import QtQuick
import QtQuick.Controls as QQC2
import QtQuick.Layouts
import org.kde.kirigami as Kirigami
import "pages"

Kirigami.ApplicationWindow {
    id: root

    title: qsTr("Borealis Tweaks")
    minimumWidth: Kirigami.Units.gridUnit * 30
    minimumHeight: Kirigami.Units.gridUnit * 30
    width: Kirigami.Units.gridUnit * 50
    height: Kirigami.Units.gridUnit * 42

    // the page on show, by name (main.py --page picks the first one)
    property string page: ""
    // what the last long job printed; every page's log shows it
    property string jobLog: ""

    readonly property var pageComponents: ({
        theme: themePage,
        bar: barPage,
        dock: dockPage,
        system: systemPage
    })

    function showPage(name) {
        const known = root.pageComponents[name] !== undefined ? name : "theme";
        if (known === root.page && pageStack.depth > 0) {
            return;
        }
        root.page = known;
        pageStack.clear();
        pageStack.push(root.pageComponents[known]);
    }

    Component.onCompleted: showPage(startPage)

    pageStack.globalToolBar.style: Kirigami.ApplicationHeaderStyle.ToolBar
    pageStack.globalToolBar.showNavigationButtons: Kirigami.ApplicationHeaderStyle.NoNavigationButtons

    globalDrawer: Kirigami.GlobalDrawer {
        title: qsTr("Borealis Tweaks")
        titleIcon: "borealis"
        isMenu: false
        modal: !root.wideScreen
        handleVisible: modal
        // just the icons while the window is narrow, so the page keeps its room
        collapsible: true
        collapsed: root.width < Kirigami.Units.gridUnit * 44
        collapseButtonVisible: false

        actions: [
            Kirigami.Action {
                text: qsTr("Theme")
                icon.name: "preferences-desktop-theme-global"
                checkable: true
                checked: root.page === "theme"
                onTriggered: root.showPage("theme")
            },
            Kirigami.Action {
                text: qsTr("Bar")
                icon.name: "application-menu"
                checkable: true
                checked: root.page === "bar"
                onTriggered: root.showPage("bar")
            },
            Kirigami.Action {
                text: qsTr("Dock")
                icon.name: "preferences-desktop-display"
                checkable: true
                checked: root.page === "dock"
                onTriggered: root.showPage("dock")
            },
            Kirigami.Action {
                text: qsTr("System")
                icon.name: "preferences-system"
                checkable: true
                checked: root.page === "system"
                onTriggered: root.showPage("system")
            }
        ]
    }

    Connections {
        target: backend
        function onLogged(line) {
            root.jobLog += line + "\n";
        }
        function onFinished(ok, message) {
            root.showPassiveNotification(message, ok ? 6000 : 12000);
        }
    }

    Component {
        id: themePage
        ThemePage {}
    }

    Component {
        id: barPage
        BarPage {}
    }

    Component {
        id: dockPage
        DockPage {}
    }

    Component {
        id: systemPage
        SystemPage {}
    }
}
