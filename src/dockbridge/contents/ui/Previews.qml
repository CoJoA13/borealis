/*
    Window previews for the dock: live pictures of an app's windows beside its
    icon while the pointer rests there. KWin draws them (live window pictures
    exist nowhere else), in a Plasma dialog so they wear the theme. Click one
    to switch to that window; middle-click or × closes it.
    SPDX-License-Identifier: GPL-3.0-or-later
*/
import QtQuick
import org.kde.kwin as KWin
import org.kde.plasma.core as PlasmaCore
import org.kde.kirigami as Kirigami

PlasmaCore.Dialog {
    id: popup

    property var entries: []                  // [{window, id}], oldest first
    property string edge: "bottom"
    property rect anchorRect: Qt.rect(0, 0, 0, 0)   // the icon, in desktop coordinates
    property rect area: Qt.rect(0, 0, 0, 0)         // the screen it's on
    readonly property bool hovered: hover.hovered

    signal activateRequested(var window)
    signal closeRequested(var window)

    readonly property bool vertical: edge !== "bottom"
    readonly property int count: Math.max(1, entries.length)
    readonly property real gap: Kirigami.Units.smallSpacing * 2
    readonly property real captionHeight: Kirigami.Units.gridUnit * 1.6
    readonly property real room: (vertical ? area.height : area.width) * 0.9 || 1600
    readonly property real cellWidth: {
        const natural = Kirigami.Units.gridUnit * 12;
        const least = Kirigami.Units.gridUnit * 7;
        if (vertical) {
            // stacked: shrink until the column fits the screen's height
            const each = room / count - gap - captionHeight;
            return Math.max(least, Math.min(natural, each / 0.62));
        }
        return Math.max(least, Math.min(natural, room / count - gap));
    }
    readonly property real thumbHeight: Math.round(cellWidth * 0.62)

    title: "dock-window-previews"
    visible: false
    location: PlasmaCore.Types.Floating
    type: PlasmaCore.Dialog.Tooltip
    flags: Qt.WindowDoesNotAcceptFocus | Qt.ToolTip
    hideOnWindowDeactivate: false
    backgroundHints: PlasmaCore.Types.StandardBackground

    function place() {
        let px, py;
        if (edge === "left") {
            px = anchorRect.x + anchorRect.width + 12;
            py = anchorRect.y + anchorRect.height / 2 - height / 2;
        } else if (edge === "right") {
            px = anchorRect.x - 12 - width;
            py = anchorRect.y + anchorRect.height / 2 - height / 2;
        } else {
            px = anchorRect.x + anchorRect.width / 2 - width / 2;
            py = anchorRect.y - 12 - height;
        }
        if (area.width > 0 && area.height > 0) {
            px = Math.max(area.x + 4, Math.min(px, area.x + area.width - width - 4));
            py = Math.max(area.y + 4, Math.min(py, area.y + area.height - height - 4));
        }
        x = Math.round(px);
        y = Math.round(py);
    }
    onWidthChanged: place()
    onHeightChanged: place()

    mainItem: Item {
        width: grid.width
        height: grid.height

        HoverHandler {
            id: hover
        }

        Grid {
            id: grid
            columns: popup.vertical ? 1 : popup.entries.length
            spacing: popup.gap

            Repeater {
                model: popup.entries
                delegate: Item {
                    id: cell
                    required property var modelData
                    readonly property var win: modelData.window

                    width: popup.cellWidth
                    height: popup.thumbHeight + popup.captionHeight

                    Rectangle {
                        anchors.fill: parent
                        radius: 10
                        color: cellHover.hovered
                            ? Qt.rgba(Kirigami.Theme.highlightColor.r, Kirigami.Theme.highlightColor.g,
                                      Kirigami.Theme.highlightColor.b, 0.22)
                            : "transparent"
                        border.width: cell.win && cell.win.active ? 1 : 0
                        border.color: Kirigami.Theme.highlightColor
                    }

                    // the window, at its own proportions, with rounded corners
                    Item {
                        id: frame
                        x: 6
                        y: 6
                        width: parent.width - 12
                        height: popup.thumbHeight - 6

                        Item {
                            id: holder
                            readonly property real ratio: thumb.implicitHeight > 0
                                ? thumb.implicitWidth / thumb.implicitHeight : 1.6
                            anchors.centerIn: parent
                            width: Math.round(Math.min(parent.width, parent.height * ratio))
                            height: Math.round(width / ratio)
                            opacity: cell.win && cell.win.minimized ? 0.6 : 1
                            layer.enabled: true
                            layer.effect: ShaderEffect {
                                property size size: Qt.size(holder.width, holder.height)
                                property real radius: 8
                                fragmentShader: Qt.resolvedUrl("roundedmask.frag.qsb")
                            }
                            KWin.WindowThumbnail {
                                id: thumb
                                anchors.fill: parent
                                wId: cell.modelData.id
                            }
                        }
                    }

                    Text {
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.bottom: parent.bottom
                        anchors.leftMargin: 8
                        anchors.rightMargin: 8
                        height: popup.captionHeight
                        verticalAlignment: Text.AlignVCenter
                        text: cell.win ? cell.win.caption : ""
                        textFormat: Text.PlainText
                        elide: Text.ElideRight
                        font.weight: cell.win && cell.win.active ? Font.DemiBold : Font.Normal
                        color: Kirigami.Theme.textColor
                    }

                    Rectangle {
                        id: closeButton
                        visible: cellHover.hovered
                        width: Kirigami.Units.gridUnit * 1.3
                        height: width
                        radius: width / 2
                        x: frame.x + frame.width - width - 4
                        y: frame.y + 4
                        color: closeHover.hovered ? "#e5484d" : Qt.rgba(0, 0, 0, 0.6)
                        Kirigami.Icon {
                            anchors.centerIn: parent
                            width: parent.width * 0.62
                            height: width
                            source: "window-close-symbolic"
                            color: "white"
                            isMask: true
                        }
                        HoverHandler {
                            id: closeHover
                        }
                        TapHandler {
                            onTapped: popup.closeRequested(cell.win)
                        }
                    }

                    HoverHandler {
                        id: cellHover
                    }
                    TapHandler {
                        acceptedButtons: Qt.LeftButton | Qt.MiddleButton
                        onTapped: (eventPoint, button) => {
                            if (closeHover.hovered) {
                                return;
                            }
                            if (button === Qt.MiddleButton) {
                                popup.closeRequested(cell.win);
                            } else {
                                popup.activateRequested(cell.win);
                            }
                        }
                    }
                }
            }
        }
    }
}
