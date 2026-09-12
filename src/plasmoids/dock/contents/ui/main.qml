/*
    Borealis Dock — launchers and running windows in one row, with the icons
    swelling under the pointer the way a Mac dock does.
    SPDX-License-Identifier: GPL-3.0-or-later
*/

import QtQuick
import QtQuick.Layouts
import org.kde.kirigami as Kirigami
import org.kde.plasma.core as PlasmaCore
import org.kde.plasma.plasmoid
import org.kde.taskmanager as TaskManager

PlasmoidItem {
    id: root

    readonly property real maxZoom: Math.max(1, Plasmoid.configuration.magnification / 100)
    readonly property int reach: Plasmoid.configuration.reach      // icons affected either side
    readonly property int gap: Kirigami.Units.smallSpacing
    readonly property int dotRow: 8                                // the running indicators
    readonly property bool horizontal: Plasmoid.formFactor !== PlasmaCore.Types.Vertical
    // how much room an icon may occupy at full magnification
    readonly property real available: Math.max(16, (horizontal ? height : width) - dotRow - gap)
    // the resting size: what the user asked for, shrunk if the panel is too
    // short for it to grow (a dock that can't magnify isn't much of a dock)
    readonly property int baseSize: Math.max(16, Math.min(Plasmoid.configuration.iconSize,
                                                          Math.floor(available / maxZoom)))
    readonly property real fitZoom: Math.min(maxZoom, available / baseSize)

    // Magnification reads the pointer against the *resting* layout: if it used
    // live positions, growing icons would move the thing being measured and
    // the dock would shiver.
    function zoomFor(restCentre, pointer) {
        if (pointer < 0) {
            return 1;
        }
        const span = baseSize * reach;
        const d = Math.abs(pointer - restCentre);
        return d > span ? 1 : 1 + (fitZoom - 1) * (Math.cos(Math.PI * d / span) + 1) / 2;
    }

    Plasmoid.backgroundHints: PlasmaCore.Types.NoBackground
    preferredRepresentation: fullRepresentation

    TaskManager.ActivityInfo { id: activityInfo }
    TaskManager.VirtualDesktopInfo { id: desktopInfo }

    TaskManager.TasksModel {
        id: tasks
        launcherList: Plasmoid.configuration.launchers
        groupMode: TaskManager.TasksModel.GroupApplications
        groupInline: false
        sortMode: TaskManager.TasksModel.SortManual
        separateLaunchers: false        // a dock: one icon per app, pinned or not
        filterByVirtualDesktop: Plasmoid.configuration.onlyCurrentDesktop
        filterByActivity: true
        filterByScreen: false
        virtualDesktop: desktopInfo.currentDesktop
        activity: activityInfo.currentActivity
        onLauncherListChanged: Plasmoid.configuration.launchers = launcherList
    }

    fullRepresentation: Item {
        id: dock

        readonly property int itemCount: Math.max(1, taskRow.count)
        // width at rest, plus the room the swell needs: constant, so the panel
        // never resizes mid-hover (that would move the icons under the cursor)
        readonly property real restWidth: itemCount * root.baseSize + (itemCount - 1) * root.gap
        readonly property real reserve: root.baseSize * (root.fitZoom - 1) * root.reach
        readonly property real restStart: (width - restWidth) / 2

        implicitWidth: root.horizontal ? restWidth + reserve : root.baseSize
        implicitHeight: root.horizontal ? root.baseSize : restWidth + reserve
        Layout.preferredWidth: implicitWidth
        Layout.minimumWidth: implicitWidth
        Layout.maximumWidth: implicitWidth

        // where the pointer is, in dock coordinates (-1 = away)
        property real pointer: -1

        function restCentreOf(index) {
            return restStart + index * (root.baseSize + root.gap) + root.baseSize / 2;
        }

        function zoomForIndex(index) {
            return root.zoomFor(restCentreOf(index), pointer);
        }

        // A HoverHandler, not a MouseArea: handlers are passive, so the icons'
        // click areas and tooltips still get their events and the pointer is
        // reported no matter what sits on top.
        HoverHandler {
            id: hover
            onPointChanged: dock.pointer = root.horizontal ? point.position.x : point.position.y
            onHoveredChanged: if (!hovered) {
                dock.pointer = -1;
            }
        }

        Row {
            id: taskRow
            anchors.centerIn: parent
            spacing: root.gap
            property int count: repeater.count + (trash.visible ? 1 : 0)

            Repeater {
                id: repeater
                model: tasks

                delegate: Item {
                    id: task

                    required property int index
                    required property var model

                    readonly property real restCentre: dock.restCentreOf(index)
                    readonly property real zoom: dock.zoomForIndex(index)
                    readonly property bool hovered: dock.pointer >= 0
                        && Math.abs(dock.pointer - restCentre) < root.baseSize / 2

                    width: root.baseSize * zoom
                    height: dock.height
                    Behavior on width { NumberAnimation { duration: 90; easing.type: Easing.OutQuad } }

                    // icon and dots travel together, centred: at rest the dock
                    // looks even, and the swell has room on both sides
                    Item {
                        id: stack
                        anchors.centerIn: parent
                        width: task.width
                        height: icon.height + root.dotRow

                        Kirigami.Icon {
                            id: icon
                            source: model.decoration
                            width: task.width
                            height: width
                            anchors.horizontalCenter: parent.horizontalCenter
                            anchors.top: parent.top
                            active: task.hovered
                            opacity: model.IsMinimized === true ? 0.55 : 1
                            Behavior on opacity { NumberAnimation { duration: Kirigami.Units.shortDuration } }
                        }

                    // running indicator: a dot per window, accent when active
                    Row {
                        id: running
                        anchors.horizontalCenter: parent.horizontalCenter
                        anchors.bottom: parent.bottom
                        spacing: 3
                        visible: model.IsWindow === true || model.IsGroupParent === true
                        Repeater {
                            model: Math.min(3, Math.max(1, task.model.ChildCount || 1))
                            Rectangle {
                                width: task.model.IsActive === true ? 6 : 4
                                height: width
                                radius: width / 2
                                color: task.model.IsActive === true
                                    ? Kirigami.Theme.highlightColor
                                    : Qt.rgba(Kirigami.Theme.textColor.r, Kirigami.Theme.textColor.g,
                                              Kirigami.Theme.textColor.b, 0.5)
                                Behavior on width { NumberAnimation { duration: Kirigami.Units.shortDuration } }
                            }
                        }
                    }
                    }

                    // a small bounce while an app starts up
                    SequentialAnimation {
                        running: model.IsStartup === true
                        loops: Animation.Infinite
                        NumberAnimation { target: stack; property: "anchors.verticalCenterOffset"
                                          to: -root.baseSize * 0.3; duration: 320
                                          easing.type: Easing.OutQuad }
                        NumberAnimation { target: stack; property: "anchors.verticalCenterOffset"
                                          to: 0; duration: 420; easing.type: Easing.OutBounce }
                    }

                    MouseArea {
                        id: mouse
                        anchors.fill: parent
                        // hover is tracked once, by the dock: a MouseArea here
                        // would swallow those events and jitter the zoom
                        hoverEnabled: false
                        acceptedButtons: Qt.LeftButton | Qt.MiddleButton | Qt.RightButton
                        onClicked: click => {
                            const idx = tasks.makeModelIndex(task.index);
                            if (click.button === Qt.MiddleButton) {
                                tasks.requestNewInstance(idx);
                            } else if (click.button === Qt.RightButton) {
                                menu.open();
                            } else if (task.model.IsActive === true && task.model.IsWindow === true) {
                                tasks.requestToggleMinimized(idx);      // click the front app to hide it
                            } else {
                                tasks.requestActivate(idx);             // launches pinned apps too
                            }
                        }
                    }

                    PlasmaCore.ToolTipArea {
                        anchors.fill: parent
                        mainText: task.model.AppName || task.model.display || ""
                        subText: task.model.IsWindow === true && task.model.display !== task.model.AppName
                            ? task.model.display : ""
                        location: Plasmoid.location
                    }

                    Loader {
                        id: menu
                        active: false
                        function open() {
                            active = true;
                        }
                        sourceComponent: TaskMenu {
                            taskIndex: task.index
                            isLauncher: task.model.IsLauncher === true
                            hasWindow: task.model.IsWindow === true
                            onClosed: menu.active = false
                        }
                        onLoaded: item.popup(task)
                    }
                }
            }

            // the dock's own trash, so it matches the icons beside it
            Item {
                id: trash
                visible: Plasmoid.configuration.showTrash
                readonly property real restCentre: dock.restCentreOf(repeater.count)
                readonly property real zoom: dock.zoomForIndex(repeater.count)
                readonly property bool hovered: dock.pointer >= 0
                    && Math.abs(dock.pointer - restCentre) < root.baseSize / 2
                width: root.baseSize * zoom
                height: dock.height
                Behavior on width { NumberAnimation { duration: 90; easing.type: Easing.OutQuad } }

                Kirigami.Icon {
                    source: "user-trash"
                    width: trash.width
                    height: width
                    anchors.horizontalCenter: parent.horizontalCenter
                    anchors.verticalCenter: parent.verticalCenter
                    anchors.verticalCenterOffset: -root.dotRow / 2   // line up with the app icons
                    active: trash.hovered
                }

                MouseArea {
                    id: trashMouse
                    anchors.fill: parent
                    hoverEnabled: false
                    onClicked: Qt.openUrlExternally("trash:/")
                }

                PlasmaCore.ToolTipArea {
                    anchors.fill: parent
                    mainText: i18nd("plasma_applet_org.borealis.dock", "Trash")
                    location: Plasmoid.location
                }
            }
        }
    }
}
