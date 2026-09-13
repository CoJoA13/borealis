/*
    New notifications, as banners under the bar. They go when they time out
    (not while the pointer rests on one), when closed, or when acted on; all
    of them stay in the clock's panel. Do Not Disturb holds them back.
    SPDX-License-Identifier: GPL-3.0-or-later
*/
import QtQuick
import QtQuick.Layouts
import org.kde.kirigami as Kirigami
import org.kde.kquickcontrolsaddons as KQuickControlsAddons
import org.kde.layershell as LayerShell

Window {
    id: banners

    property var notices: null
    readonly property var model: notices ? notices.popups : null
    readonly property bool centered: bar.settings.values.bannerPosition === "center"
    property int commitTick: 0

    title: "Notifications"
    color: "transparent"
    visible: bar.settings.values.banners && !!model && repeater.count > 0
    width: 400
    height: Math.max(1, column.implicitHeight + 16)

    LayerShell.Window.scope: "bar-notifications"
    LayerShell.Window.layer: LayerShell.Window.LayerOverlay
    LayerShell.Window.anchors: centered ? LayerShell.Window.AnchorTop
        : (LayerShell.Window.AnchorTop | LayerShell.Window.AnchorRight)
    LayerShell.Window.exclusionZone: 0
    LayerShell.Window.keyboardInteractivity: LayerShell.Window.KeyboardInteractivityNone

    Kirigami.Theme.colorSet: Kirigami.Theme.Window
    Kirigami.Theme.inherit: false

    // only the banners themselves take clicks; the rest of the surface lets them through
    function pushSurface() {
        const rects = [];
        for (let i = 0; i < repeater.count; i++) {
            const b = repeater.itemAt(i);
            if (b) {
                rects.push(Qt.rect(column.x + b.x, column.y + b.y, b.width, b.height));
            }
        }
        bar.updateSurface(banners, rects.length ? rects : [Qt.rect(0, 0, 1, 1)], Qt.rect(0, 0, 0, 0), -1);
    }
    onHeightChanged: Qt.callLater(pushSurface)
    onVisibleChanged: Qt.callLater(pushSurface)

    ColumnLayout {
        id: column
        x: 8
        y: 8
        width: banners.width - 16
        spacing: 8

        Repeater {
            id: repeater
            model: banners.model
            delegate: Rectangle {
                id: banner
                required property var model
                required property int index
                readonly property color fg: Kirigami.Theme.textColor
                readonly property bool isJob: !!banners.notices && model.type === banners.notices.jobType

                Layout.fillWidth: true
                implicitHeight: content.implicitHeight + 24
                radius: 14
                color: Qt.rgba(Kirigami.Theme.backgroundColor.r, Kirigami.Theme.backgroundColor.g,
                               Kirigami.Theme.backgroundColor.b, 0.96)
                border.width: 1
                border.color: Qt.rgba(fg.r, fg.g, fg.b, 0.16)

                Component.onCompleted: {
                    if (!isJob) {
                        banners.notices.startTimeout(index);
                    }
                    Qt.callLater(banners.pushSurface);
                }

                MouseArea {
                    anchors.fill: parent
                    hoverEnabled: true
                    onContainsMouseChanged: {
                        if (banner.isJob) {
                            return;
                        }
                        if (containsMouse) {
                            banners.notices.stopTimeout(banner.index);
                        } else {
                            banners.notices.startTimeout(banner.index);
                        }
                    }
                    onClicked: {
                        if (banner.model.hasDefaultAction === true) {
                            banners.notices.activate(banners.model, banner.index);
                        } else {
                            banners.notices.expire(banner.index);
                        }
                    }
                }

                RowLayout {
                    id: content
                    x: 12
                    y: 12
                    width: banner.width - 24
                    spacing: 12

                    Item {
                        Layout.preferredWidth: 36
                        Layout.preferredHeight: 36
                        Layout.alignment: Qt.AlignTop
                        Kirigami.Icon {
                            anchors.fill: parent
                            visible: !banner.model.image
                            source: banner.model.iconName || banner.model.applicationIconName
                                    || "preferences-desktop-notification-bell"
                        }
                        KQuickControlsAddons.QImageItem {
                            anchors.fill: parent
                            visible: !!banner.model.image
                            image: banner.model.image
                            fillMode: KQuickControlsAddons.QImageItem.PreserveAspectFit
                        }
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 2
                        RowLayout {
                            Layout.fillWidth: true
                            Text {
                                Layout.fillWidth: true
                                text: banner.model.applicationName || ""
                                textFormat: Text.PlainText
                                elide: Text.ElideRight
                                font.pointSize: Kirigami.Theme.smallFont.pointSize
                                color: Kirigami.Theme.disabledTextColor
                            }
                            Text {
                                text: "✕"
                                font.pointSize: Kirigami.Theme.smallFont.pointSize
                                color: closeArea.containsMouse ? Kirigami.Theme.textColor : Kirigami.Theme.disabledTextColor
                                MouseArea {
                                    id: closeArea
                                    anchors.fill: parent
                                    anchors.margins: -6
                                    hoverEnabled: true
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: banners.notices.close(banners.model, banner.index)
                                }
                            }
                        }
                        Text {
                            Layout.fillWidth: true
                            visible: text.length > 0
                            text: banner.model.summary || ""
                            textFormat: Text.PlainText
                            wrapMode: Text.Wrap
                            maximumLineCount: 2
                            elide: Text.ElideRight
                            font.bold: true
                            font.pointSize: Kirigami.Theme.defaultFont.pointSize
                            color: Kirigami.Theme.textColor
                        }
                        Text {
                            Layout.fillWidth: true
                            visible: text.length > 0
                            text: (banner.model.body || "").replace(/^<\?xml[^>]*>/, "")
                            textFormat: Text.StyledText
                            wrapMode: Text.Wrap
                            maximumLineCount: 3
                            elide: Text.ElideRight
                            font.pointSize: Kirigami.Theme.defaultFont.pointSize
                            color: Kirigami.Theme.textColor
                            opacity: 0.85
                        }
                        Rectangle {
                            Layout.fillWidth: true
                            Layout.topMargin: 4
                            visible: banner.isJob
                            height: 4
                            radius: 2
                            color: Qt.rgba(banner.fg.r, banner.fg.g, banner.fg.b, 0.15)
                            Rectangle {
                                width: parent.width * Math.max(0, Math.min(100, banner.model.percentage || 0)) / 100
                                height: parent.height
                                radius: 2
                                color: Kirigami.Theme.highlightColor
                            }
                        }
                        Flow {
                            Layout.fillWidth: true
                            Layout.topMargin: 6
                            visible: (banner.model.actionLabels || []).length > 0
                            spacing: 6
                            Repeater {
                                model: banner.model.actionLabels || []
                                delegate: TextButton {
                                    required property string modelData
                                    required property int index
                                    text: modelData
                                    onClicked: banners.notices.action(banners.model, banner.index,
                                                                      banner.model.actionNames[index])
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    Rectangle {
        width: 1
        height: 1
        color: banners.commitTick % 2 ? "#01000000" : "#02000000"
    }
}
