/*
    One notification in the clock's panel (or an app's heading, when several
    of its notifications are grouped).
    SPDX-License-Identifier: GPL-3.0-or-later
*/
import QtQuick
import QtQuick.Layouts
import org.kde.kirigami as Kirigami
import org.kde.kquickcontrolsaddons as KQuickControlsAddons

Rectangle {
    id: row

    required property var model
    required property int index
    property var notices: null
    property var source: null
    readonly property color fg: Kirigami.Theme.textColor
    readonly property bool isGroup: model.isGroup === true
    readonly property bool isJob: !!notices && model.type === notices.jobType

    implicitHeight: isGroup ? heading.implicitHeight + 8 : layout.implicitHeight + 16
    radius: 10
    color: isGroup ? "transparent" : hover.hovered ? Qt.rgba(fg.r, fg.g, fg.b, 0.10) : Qt.rgba(fg.r, fg.g, fg.b, 0.05)

    HoverHandler {
        id: hover
    }
    TapHandler {
        enabled: !row.isGroup && row.model.hasDefaultAction === true
        onTapped: row.notices.activate(row.source, row.index)
    }

    Text {
        id: heading
        visible: row.isGroup
        x: 4
        y: 6
        text: row.model.applicationName || ""
        textFormat: Text.PlainText
        font.bold: true
        font.pointSize: Kirigami.Theme.smallFont.pointSize
        color: Kirigami.Theme.disabledTextColor
    }

    RowLayout {
        id: layout
        visible: !row.isGroup
        x: 8
        y: 8
        width: row.width - 16
        spacing: 10

        Item {
            Layout.preferredWidth: 32
            Layout.preferredHeight: 32
            Layout.alignment: Qt.AlignTop
            Kirigami.Icon {
                anchors.fill: parent
                visible: !row.model.image
                source: row.model.iconName || row.model.applicationIconName || "preferences-desktop-notification-bell"
            }
            KQuickControlsAddons.QImageItem {
                anchors.fill: parent
                visible: !!row.model.image
                image: row.model.image
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
                    text: row.model.applicationName || ""
                    textFormat: Text.PlainText
                    elide: Text.ElideRight
                    font.pointSize: Kirigami.Theme.smallFont.pointSize
                    color: Kirigami.Theme.disabledTextColor
                }
                Text {
                    text: row.model.created ? row.model.created.toLocaleTimeString(Qt.locale(), Locale.ShortFormat) : ""
                    font.pointSize: Kirigami.Theme.smallFont.pointSize
                    color: Kirigami.Theme.disabledTextColor
                }
                Text {
                    text: "✕"
                    font.pointSize: Kirigami.Theme.smallFont.pointSize
                    color: closeHover.hovered ? Kirigami.Theme.textColor : Kirigami.Theme.disabledTextColor
                    HoverHandler {
                        id: closeHover
                        cursorShape: Qt.PointingHandCursor
                    }
                    TapHandler {
                        onTapped: row.notices.close(row.source, row.index)
                    }
                }
            }
            Text {
                Layout.fillWidth: true
                visible: text.length > 0
                text: row.model.summary || ""
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
                text: (row.model.body || "").replace(/^<\?xml[^>]*>/, "")
                textFormat: Text.StyledText
                wrapMode: Text.Wrap
                maximumLineCount: 4
                elide: Text.ElideRight
                font.pointSize: Kirigami.Theme.defaultFont.pointSize
                color: Kirigami.Theme.textColor
                opacity: 0.85
            }
            Rectangle {
                Layout.fillWidth: true
                Layout.topMargin: 4
                visible: row.isJob
                height: 4
                radius: 2
                color: Qt.rgba(row.fg.r, row.fg.g, row.fg.b, 0.15)
                Rectangle {
                    width: parent.width * Math.max(0, Math.min(100, row.model.percentage || 0)) / 100
                    height: parent.height
                    radius: 2
                    color: Kirigami.Theme.highlightColor
                }
            }
            Flow {
                Layout.fillWidth: true
                Layout.topMargin: 4
                visible: (row.model.actionLabels || []).length > 0
                spacing: 6
                Repeater {
                    model: row.model.actionLabels || []
                    delegate: TextButton {
                        required property string modelData
                        required property int index
                        text: modelData
                        onClicked: row.notices.action(row.source, row.index, row.model.actionNames[index])
                    }
                }
            }
        }
    }
}
