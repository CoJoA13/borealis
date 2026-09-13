/*
    An on/off switch for the bar's panels. It asks rather than flips: the
    owner sets `checked` from what the setting really is.
    SPDX-License-Identifier: GPL-3.0-or-later
*/
import QtQuick
import org.kde.kirigami as Kirigami

Item {
    id: toggle

    property bool checked: false
    property string tip
    signal toggled(bool checked)

    readonly property color fg: Kirigami.Theme.textColor
    implicitWidth: 42
    implicitHeight: 24
    opacity: enabled ? 1 : 0.4
    Accessible.role: Accessible.CheckBox
    Accessible.checkable: true
    Accessible.checked: checked
    Accessible.name: tip

    Rectangle {
        anchors.fill: parent
        radius: height / 2
        color: toggle.checked ? Kirigami.Theme.highlightColor : Qt.rgba(toggle.fg.r, toggle.fg.g, toggle.fg.b, 0.2)
        Behavior on color {
            ColorAnimation {
                duration: 120
            }
        }
        Rectangle {
            y: 3
            x: toggle.checked ? parent.width - width - 3 : 3
            width: parent.height - 6
            height: width
            radius: width / 2
            color: toggle.checked ? Kirigami.Theme.highlightedTextColor
                                  : Qt.rgba(toggle.fg.r, toggle.fg.g, toggle.fg.b, 0.85)
            Behavior on x {
                NumberAnimation {
                    duration: 120
                    easing.type: Easing.OutCubic
                }
            }
        }
    }
    HoverHandler {
        cursorShape: Qt.PointingHandCursor
    }
    TapHandler {
        gesturePolicy: TapHandler.ReleaseWithinBounds
        onTapped: toggle.toggled(!toggle.checked)
    }
}
