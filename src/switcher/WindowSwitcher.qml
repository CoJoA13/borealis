/*
    Borealis task switcher (Alt+Tab): a frosted card of rounded window
    previews with icon + title rows. Based on KWin's thumbnail_grid switcher.

    SPDX-FileCopyrightText: 2020 Chris Holland <zrenfire@gmail.com>
    SPDX-FileCopyrightText: 2023 Nate Graham <nate@kde.org>
    SPDX-License-Identifier: GPL-2.0-or-later
*/

import QtQuick
import QtQuick.Layouts
import org.kde.plasma.core as PlasmaCore
import org.kde.ksvg as KSvg
import org.kde.plasma.components as PlasmaComponents3
import org.kde.kwin as KWin
import org.kde.kirigami as Kirigami

KWin.TabBoxSwitcher {
    id: tabBox

    Instantiator {
        active: tabBox.visible
        delegate: PlasmaCore.Dialog {
            location: PlasmaCore.Types.Floating
            visible: true
            flags: Qt.Popup | Qt.X11BypassWindowManagerHint
            x: tabBox.screenGeometry.x + tabBox.screenGeometry.width * 0.5 - dialogMainItem.width * 0.5
            y: tabBox.screenGeometry.y + tabBox.screenGeometry.height * 0.5 - dialogMainItem.height * 0.5

            mainItem: FocusScope {
                id: dialogMainItem

                focus: true

                property int maxWidth: tabBox.screenGeometry.width * 0.9
                property int maxHeight: tabBox.screenGeometry.height * 0.7
                property real screenFactor: tabBox.screenGeometry.width / tabBox.screenGeometry.height
                property int maxColumns: Math.max(1, Math.floor(maxWidth / grid.cellWidth))
                // one row when it fits, otherwise a balanced grid
                property int columns: {
                    const n = Math.max(1, grid.count);
                    if (n <= maxColumns) {
                        return n;
                    }
                    return Math.min(maxColumns, Math.ceil(n / Math.ceil(n / maxColumns)));
                }
                property int rows: Math.ceil(grid.count / columns)
                width: Math.min(Math.max(grid.cellWidth, grid.cellWidth * columns), maxWidth)
                height: Math.min(Math.max(grid.cellHeight, grid.cellHeight * rows), maxHeight)
                clip: true

                KSvg.FrameSvgItem {
                    id: frameMetrics
                    imagePath: "widgets/viewitem"
                    prefix: "hover"
                    visible: false
                }

                GridView {
                    id: grid
                    anchors.fill: parent
                    focus: true
                    model: tabBox.model
                    currentIndex: tabBox.currentIndex

                    readonly property int pad: Kirigami.Units.largeSpacing
                    readonly property int thumbWidth: Kirigami.Units.gridUnit * 13
                    readonly property int thumbHeight: Math.round(thumbWidth / dialogMainItem.screenFactor)
                    readonly property int captionHeight: Kirigami.Units.gridUnit * 2
                    cellWidth: thumbWidth + pad * 2
                    cellHeight: thumbHeight + captionHeight + pad * 2

                    keyNavigationWraps: true
                    highlightMoveDuration: Kirigami.Units.shortDuration

                    delegate: MouseArea {
                        id: cell
                        width: grid.cellWidth
                        height: grid.cellHeight
                        focus: GridView.isCurrentItem
                        hoverEnabled: true

                        Accessible.name: model.caption
                        Accessible.role: Accessible.ListItem

                        onClicked: tabBox.model.activate(index)

                        Item {
                            id: preview
                            x: grid.pad
                            y: grid.pad
                            width: grid.thumbWidth
                            height: grid.thumbHeight

                            // rounded window preview, sized to the window's own aspect ratio
                            Item {
                                id: thumbHolder
                                readonly property real ratio: thumb.implicitHeight > 0
                                    ? thumb.implicitWidth / thumb.implicitHeight : dialogMainItem.screenFactor
                                anchors.centerIn: parent
                                width: Math.round(Math.min(parent.width, parent.height * ratio))
                                height: Math.round(width / ratio)
                                opacity: model.minimized ? 0.55 : 1
                                layer.enabled: true
                                layer.effect: ShaderEffect {
                                    property size size: Qt.size(thumbHolder.width, thumbHolder.height)
                                    property real radius: 10
                                    fragmentShader: Qt.resolvedUrl("roundedmask.frag.qsb")
                                }
                                KWin.WindowThumbnail {
                                    id: thumb
                                    anchors.fill: parent
                                    wId: windowId
                                }
                            }

                            Rectangle {
                                anchors.fill: thumbHolder
                                radius: 10
                                color: "transparent"
                                border.width: 1
                                border.color: Qt.rgba(Kirigami.Theme.textColor.r, Kirigami.Theme.textColor.g,
                                                      Kirigami.Theme.textColor.b, 0.12)
                            }

                            PlasmaComponents3.Button {
                                id: closeButton
                                anchors {
                                    right: thumbHolder.right
                                    top: thumbHolder.top
                                    margins: Kirigami.Units.smallSpacing
                                }
                                visible: model.closeable && typeof tabBox.model.close !== 'undefined'
                                    && (cell.containsMouse || closeButton.hovered || cell.focus
                                        || Kirigami.Settings.tabletMode || Kirigami.Settings.hasTransientTouchInput)
                                icon.name: "window-close-symbolic"
                                onClicked: tabBox.model.close(index)
                            }
                        }

                        RowLayout {
                            anchors {
                                left: preview.left
                                right: preview.right
                                top: preview.bottom
                                topMargin: Kirigami.Units.smallSpacing
                            }
                            height: grid.captionHeight - Kirigami.Units.smallSpacing
                            spacing: Kirigami.Units.smallSpacing

                            Kirigami.Icon {
                                Layout.preferredWidth: Kirigami.Units.iconSizes.smallMedium
                                Layout.preferredHeight: Kirigami.Units.iconSizes.smallMedium
                                source: model.icon
                            }
                            PlasmaComponents3.Label {
                                Layout.fillWidth: true
                                text: model.caption
                                textFormat: Text.PlainText
                                elide: Text.ElideRight
                                font.weight: cell.GridView.isCurrentItem ? Font.DemiBold : Font.Normal
                            }
                        }
                    }

                    highlight: KSvg.FrameSvgItem {
                        imagePath: "widgets/viewitem"
                        prefix: "selected+hover"
                    }

                    onCurrentIndexChanged: tabBox.currentIndex = grid.currentIndex
                }

                Kirigami.PlaceholderMessage {
                    anchors.centerIn: parent
                    width: parent.width - Kirigami.Units.largeSpacing * 2
                    icon.source: "edit-none"
                    text: i18ndc("kwin", "@info:placeholder no entries in the task switcher", "No open windows")
                    visible: grid.count === 0
                }

                Keys.onPressed: event => {
                    if (event.key === Qt.Key_Left) {
                        grid.moveCurrentIndexLeft();
                    } else if (event.key === Qt.Key_Right) {
                        grid.moveCurrentIndexRight();
                    } else if (event.key === Qt.Key_Up) {
                        grid.moveCurrentIndexUp();
                    } else if (event.key === Qt.Key_Down) {
                        grid.moveCurrentIndexDown();
                    } else {
                        return;
                    }
                    grid.currentIndexChanged(grid.currentIndex);
                }
            }

            onSceneGraphError: () => {
                // intentionally empty: avoid qFatal on a graphics reset
            }
        }
    }
}
