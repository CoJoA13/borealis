/*
    The top of a Control Center page: back, the page's name, and a switch for
    the thing the page is about.
    SPDX-License-Identifier: GPL-3.0-or-later
*/
import QtQuick
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

RowLayout {
    id: header

    property string title
    property bool switchVisible: false
    property bool checked: false
    property bool switchEnabled: true
    property bool busy: false
    signal back()
    signal toggled(bool checked)

    spacing: 8

    IconButton {
        objectName: "page-back"
        iconName: "go-previous"
        tip: qsTr("Back")
        onClicked: header.back()
    }
    Text {
        Layout.fillWidth: true
        text: header.title
        textFormat: Text.PlainText
        elide: Text.ElideRight
        font.pointSize: Kirigami.Theme.defaultFont.pointSize * 1.15
        font.weight: Font.DemiBold
        color: Kirigami.Theme.textColor
    }
    Kirigami.Icon {
        visible: header.busy
        source: "view-refresh"
        Layout.preferredWidth: 16
        Layout.preferredHeight: 16
        RotationAnimator on rotation {
            running: header.busy && header.visible
            from: 0
            to: 360
            duration: 1000
            loops: Animation.Infinite
        }
    }
    ToggleSwitch {
        objectName: "page-switch"
        visible: header.switchVisible
        enabled: header.switchEnabled
        checked: header.checked
        tip: header.title
        onToggled: on => header.toggled(on)
    }
}
