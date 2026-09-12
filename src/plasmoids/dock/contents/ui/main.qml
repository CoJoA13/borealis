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

    readonly property int baseSize: Plasmoid.configuration.iconSize
    readonly property real maxZoom: Plasmoid.configuration.magnification / 100
    readonly property int reach: Plasmoid.configuration.reach      // icons affected either side
    readonly property int gap: Kirigami.Units.smallSpacing
    // the zoomed icon has to fit the panel, so cap the growth by the height
    readonly property real fitZoom: Math.min(maxZoom, Math.max(1, (height - gap * 2) / baseSize))
    readonly property bool horizontal: Plasmoid.formFactor !== PlasmaCore.Types.Vertical

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
        implicitWidth: root.horizontal ? taskRow.implicitWidth : root.baseSize
        implicitHeight: root.horizontal ? root.baseSize : taskRow.implicitHeight
        Layout.preferredWidth: implicitWidth
        Layout.minimumWidth: implicitWidth
        Layout.maximumWidth: implicitWidth

        // where the pointer is, in dock coordinates (-1 = away)
        property real pointer: -1

        MouseArea {
            id: hover
            anchors.fill: parent
            hoverEnabled: true
            acceptedButtons: Qt.NoButton
            onPositionChanged: mouse => dock.pointer = root.horizontal ? mouse.x : mouse.y
            onExited: dock.pointer = -1
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

                    readonly property real centre: x + width / 2
                    // cosine falloff: nearest icon grows most, neighbours follow
                    readonly property real distance: dock.pointer < 0 ? 9999
                        : Math.abs(dock.pointer - (taskRow.x + centre))
                    readonly property real span: root.baseSize * root.reach
                    readonly property real zoom: distance > span ? 1
                        : 1 + (root.fitZoom - 1) * (Math.cos(Math.PI * distance / span) + 1) / 2

                    width: root.baseSize * zoom
                    height: dock.height
                    Behavior on width { NumberAnimation { duration: 90; easing.type: Easing.OutQuad } }

                    Kirigami.Icon {
                        id: icon
                        source: model.decoration
                        width: task.width - root.gap
                        height: width
                        anchors.horizontalCenter: parent.horizontalCenter
                        anchors.bottom: parent.bottom
                        anchors.bottomMargin: running.height + root.gap / 2
                        active: mouse.containsMouse
                        opacity: model.IsMinimized === true ? 0.55 : 1
                        Behavior on opacity { NumberAnimation { duration: Kirigami.Units.shortDuration } }
                    }

                    // running indicator: a dot per window, accent when active
                    Row {
                        id: running
                        anchors.horizontalCenter: parent.horizontalCenter
                        anchors.bottom: parent.bottom
                        anchors.bottomMargin: 2
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

                    // a small bounce while an app starts up
                    SequentialAnimation {
                        running: model.IsStartup === true
                        loops: Animation.Infinite
                        NumberAnimation { target: icon; property: "anchors.bottomMargin"
                                          to: running.height + root.baseSize * 0.35; duration: 320
                                          easing.type: Easing.OutQuad }
                        NumberAnimation { target: icon; property: "anchors.bottomMargin"
                                          to: running.height + root.gap / 2; duration: 420
                                          easing.type: Easing.OutBounce }
                    }

                    MouseArea {
                        id: mouse
                        anchors.fill: parent
                        hoverEnabled: true
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
                        onPositionChanged: pos => dock.pointer = root.horizontal
                            ? task.x + pos.x : task.y + pos.y
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
                readonly property real centre: x + width / 2
                readonly property real distance: dock.pointer < 0 ? 9999
                    : Math.abs(dock.pointer - (taskRow.x + centre))
                readonly property real span: root.baseSize * root.reach
                readonly property real zoom: distance > span ? 1
                    : 1 + (root.fitZoom - 1) * (Math.cos(Math.PI * distance / span) + 1) / 2
                width: root.baseSize * zoom
                height: dock.height
                Behavior on width { NumberAnimation { duration: 90; easing.type: Easing.OutQuad } }

                Kirigami.Icon {
                    source: "user-trash"
                    width: trash.width - root.gap
                    height: width
                    anchors.horizontalCenter: parent.horizontalCenter
                    anchors.bottom: parent.bottom
                    anchors.bottomMargin: root.gap * 1.5
                    active: trashMouse.containsMouse
                }

                MouseArea {
                    id: trashMouse
                    anchors.fill: parent
                    hoverEnabled: true
                    onClicked: Qt.openUrlExternally("trash:/")
                    onPositionChanged: pos => dock.pointer = root.horizontal
                        ? trash.x + pos.x : trash.y + pos.y
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
