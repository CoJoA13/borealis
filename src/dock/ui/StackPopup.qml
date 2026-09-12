/*
    A Stack, opened: its newest items fanned out above the icon (up to eight,
    bottom dock), or a grid for more. Click an item to open it, drag it out to
    use it elsewhere, or open the whole folder.
    SPDX-License-Identifier: GPL-3.0-or-later
*/
import QtQuick
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

Item {
    id: popup

    property var entries: []
    property string title: ""
    property string view: "auto"
    property string edge: "bottom"
    property rect anchorRect: Qt.rect(0, 0, 0, 0)

    signal opened(string url)
    signal openFolder()
    signal dismissed()
    signal dragStarted()
    signal dragFinished()

    readonly property int fanCount: Math.min(entries.length, 8)
    readonly property bool fan: edge === "bottom" && entries.length > 0
        && (view === "fan" || (view === "auto" && entries.length <= 8))
    readonly property real cell: 54
    readonly property real centre: anchorRect.x + anchorRect.width / 2
    readonly property real fanTop: anchorRect.y - 16 - (fanCount + 1) * (cell + 10)
    readonly property rect inputRect: fan
        ? Qt.rect(centre - 340, fanTop, 460, anchorRect.y - fanTop)
        : Qt.rect(grid.x, grid.y, grid.width, grid.height)
    readonly property rect blurRect: fan ? Qt.rect(0, 0, 0, 0) : Qt.rect(grid.x, grid.y, grid.width, grid.height)
    readonly property real blurRadius: grid.radius

    focus: true
    Keys.onEscapePressed: dismissed()

    function clamp(v, lo, hi) {
        return Math.max(lo, Math.min(hi, v));
    }

    // an item's picture: a thumbnail for images, its type's icon otherwise
    component Glyph: Item {
        property var entry
        Rectangle {
            anchors.fill: parent
            visible: !!parent.entry && parent.entry.image
            radius: width * 0.1
            color: "white"
            Image {
                anchors.fill: parent
                anchors.margins: parent.width * 0.05
                source: parent.visible ? parent.parent.entry.url : ""
                sourceSize.width: 160
                sourceSize.height: 160
                fillMode: Image.PreserveAspectCrop
                asynchronous: true
            }
        }
        Kirigami.Icon {
            anchors.fill: parent
            visible: !!parent.entry && !parent.entry.image
            source: parent.entry ? parent.entry.icon : ""
            roundToIconSize: false
        }
    }

    // dragging an item out hands the file to whatever it's dropped on
    component Draggable: Item {
        id: draggable
        property var entry
        Drag.active: dragHandler.active
        Drag.dragType: Drag.Automatic
        Drag.supportedActions: Qt.CopyAction | Qt.MoveAction | Qt.LinkAction
        Drag.mimeData: ({ "text/uri-list": draggable.entry ? draggable.entry.url + "\r\n" : "" })
        Drag.onDragStarted: popup.dragStarted()
        Drag.onDragFinished: popup.dragFinished()
        DragHandler {
            id: dragHandler
            target: null
            dragThreshold: 8
        }
        TapHandler {
            onTapped: popup.opened(draggable.entry.url)
        }
    }

    // ---- fan ------------------------------------------------------------------
    Repeater {
        model: popup.fan ? popup.fanCount : 0
        delegate: Item {
            id: fanItem
            required property int index
            readonly property var entry: popup.entries[index]
            readonly property real t: (index + 1) / (popup.fanCount + 1)
            property bool shown: false

            width: popup.cell
            height: popup.cell
            x: popup.centre - width / 2 + 80 * t * t
            y: popup.anchorRect.y - 16 - (index + 1) * (popup.cell + 10)
            rotation: 8 * t
            opacity: shown ? 1 : 0
            scale: shown ? 1 : 0.4
            Behavior on opacity { NumberAnimation { duration: 120 + fanItem.index * 25 } }
            Behavior on scale { NumberAnimation { duration: 160 + fanItem.index * 25; easing.type: Easing.OutBack } }
            Component.onCompleted: Qt.callLater(() => { fanItem.shown = true; })

            Glyph {
                anchors.fill: parent
                entry: fanItem.entry
            }
            Rectangle {
                anchors.right: parent.left
                anchors.rightMargin: 10
                anchors.verticalCenter: parent.verticalCenter
                width: Math.min(280, fanName.implicitWidth) + 20
                height: fanName.implicitHeight + 8
                radius: height / 2
                color: fanHover.hovered ? Kirigami.Theme.highlightColor : Qt.rgba(0.05, 0.07, 0.11, 0.78)
                Text {
                    id: fanName
                    anchors.centerIn: parent
                    width: Math.min(280, implicitWidth)
                    text: fanItem.entry.name
                    elide: Text.ElideMiddle
                    color: "white"
                    font.pointSize: Kirigami.Theme.defaultFont.pointSize
                }
            }
            HoverHandler { id: fanHover }
            Draggable {
                anchors.fill: parent
                entry: fanItem.entry
            }
        }
    }

    // the folder itself, at the top of the fan
    Rectangle {
        visible: popup.fan
        width: 40
        height: 40
        radius: 20
        x: popup.centre - width / 2 + 80
        y: popup.fanTop + (popup.cell - height) / 2
        color: folderHover.hovered ? Kirigami.Theme.highlightColor : Qt.rgba(0.05, 0.07, 0.11, 0.78)
        Kirigami.Icon {
            anchors.centerIn: parent
            width: 22
            height: 22
            source: "document-open-folder"
            color: "white"
        }
        HoverHandler { id: folderHover }
        TapHandler { onTapped: popup.openFolder() }
    }

    // ---- grid -----------------------------------------------------------------
    Rectangle {
        id: grid
        Kirigami.Theme.colorSet: Kirigami.Theme.Window
        Kirigami.Theme.inherit: false

        readonly property int columns: Math.max(3, Math.min(6, Math.ceil(Math.sqrt(Math.max(1, popup.entries.length)))))
        readonly property real cellWidth: 108
        readonly property real cellHeight: 104
        readonly property int rows: Math.max(1, Math.ceil(popup.entries.length / columns))

        visible: !popup.fan
        width: columns * cellWidth + 24
        height: Math.min(popup.height * 0.7, header.height + rows * cellHeight + 28)
        x: popup.clamp(popup.edge === "bottom" ? popup.centre - width / 2
                       : popup.edge === "left" ? popup.anchorRect.x + popup.anchorRect.width + 14
                       : popup.anchorRect.x - width - 14,
                       8, Math.max(8, popup.width - width - 8))
        y: popup.clamp(popup.edge === "bottom" ? popup.anchorRect.y - height - 14
                       : popup.anchorRect.y + popup.anchorRect.height / 2 - height / 2,
                       8, Math.max(8, popup.height - height - 8))
        radius: 14
        color: Qt.rgba(Kirigami.Theme.backgroundColor.r, Kirigami.Theme.backgroundColor.g,
                       Kirigami.Theme.backgroundColor.b, 0.86)
        border.width: 1
        border.color: Qt.rgba(Kirigami.Theme.textColor.r, Kirigami.Theme.textColor.g, Kirigami.Theme.textColor.b, 0.14)

        MouseArea {
            anchors.fill: parent             // clicks inside never reach the overlay
            acceptedButtons: Qt.AllButtons
        }

        RowLayout {
            id: header
            x: 16
            y: 10
            width: parent.width - 32
            height: 34
            Text {
                Layout.fillWidth: true
                text: popup.title
                elide: Text.ElideRight
                font.bold: true
                font.pointSize: Kirigami.Theme.defaultFont.pointSize * 1.1
                color: Kirigami.Theme.textColor
            }
            Rectangle {
                Layout.preferredHeight: 28
                Layout.preferredWidth: openLabel.implicitWidth + 44
                radius: 14
                color: openHover.hovered ? Kirigami.Theme.highlightColor
                                         : Qt.rgba(Kirigami.Theme.textColor.r, Kirigami.Theme.textColor.g,
                                                   Kirigami.Theme.textColor.b, 0.1)
                RowLayout {
                    anchors.centerIn: parent
                    spacing: 6
                    Kirigami.Icon {
                        Layout.preferredWidth: 16
                        Layout.preferredHeight: 16
                        source: "document-open-folder"
                    }
                    Text {
                        id: openLabel
                        text: qsTr("Open folder")
                        color: openHover.hovered ? Kirigami.Theme.highlightedTextColor : Kirigami.Theme.textColor
                        font.pointSize: Kirigami.Theme.defaultFont.pointSize
                    }
                }
                HoverHandler { id: openHover }
                TapHandler { onTapped: popup.openFolder() }
            }
        }

        Text {
            anchors.centerIn: parent
            visible: popup.entries.length === 0
            text: qsTr("“%1” is empty").arg(popup.title)
            color: Kirigami.Theme.disabledTextColor
            font.pointSize: Kirigami.Theme.defaultFont.pointSize
        }

        GridView {
            id: gridView
            x: 12
            y: header.y + header.height + 8
            width: parent.width - 24
            height: parent.height - y - 12
            clip: true
            cellWidth: grid.cellWidth
            cellHeight: grid.cellHeight
            model: popup.fan ? [] : popup.entries
            boundsBehavior: Flickable.StopAtBounds

            delegate: Item {
                id: cellItem
                required property var modelData
                width: grid.cellWidth
                height: grid.cellHeight

                Rectangle {
                    anchors.fill: parent
                    anchors.margins: 3
                    radius: 10
                    visible: cellHover.hovered
                    color: Qt.rgba(Kirigami.Theme.highlightColor.r, Kirigami.Theme.highlightColor.g,
                                   Kirigami.Theme.highlightColor.b, 0.25)
                }
                Glyph {
                    id: cellGlyph
                    width: 56
                    height: 56
                    anchors.horizontalCenter: parent.horizontalCenter
                    y: 8
                    entry: cellItem.modelData
                }
                Text {
                    anchors.top: cellGlyph.bottom
                    anchors.topMargin: 6
                    anchors.horizontalCenter: parent.horizontalCenter
                    width: parent.width - 10
                    horizontalAlignment: Text.AlignHCenter
                    text: cellItem.modelData.name
                    elide: Text.ElideMiddle
                    maximumLineCount: 2
                    wrapMode: Text.WrapAnywhere
                    color: Kirigami.Theme.textColor
                    font.pointSize: Kirigami.Theme.smallFont.pointSize
                }
                HoverHandler { id: cellHover }
                Draggable {
                    anchors.fill: parent
                    entry: cellItem.modelData
                }
            }
        }
    }
}
