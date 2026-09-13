/*
    A text field for the bar's panels, with a button to show a password.
    SPDX-License-Identifier: GPL-3.0-or-later
*/
import QtQuick
import org.kde.kirigami as Kirigami

Rectangle {
    id: field

    property alias text: input.text
    property string placeholder
    property bool password: false
    property bool revealed: false
    property int minimumLength: 0
    // Escape cancels whatever the field is part of; otherwise it goes on to
    // the panel (which goes back a page, or closes)
    property bool catchesEscape: false
    readonly property bool acceptable: input.text.length >= minimumLength
    signal accepted()
    signal cancelled()

    readonly property color fg: Kirigami.Theme.textColor
    function focusInput() {
        input.forceActiveFocus();
    }

    implicitWidth: 200
    implicitHeight: 34
    radius: 8
    opacity: enabled ? 1 : 0.5
    color: Qt.rgba(fg.r, fg.g, fg.b, 0.07)
    border.width: input.activeFocus ? 2 : 1
    border.color: input.activeFocus ? Kirigami.Theme.highlightColor : Qt.rgba(fg.r, fg.g, fg.b, 0.18)

    TextInput {
        id: input
        anchors.left: parent.left
        anchors.right: eye.visible ? eye.left : parent.right
        anchors.verticalCenter: parent.verticalCenter
        anchors.leftMargin: 10
        anchors.rightMargin: 8
        clip: true
        selectByMouse: true
        echoMode: field.password && !field.revealed ? TextInput.Password : TextInput.Normal
        color: Kirigami.Theme.textColor
        selectionColor: Kirigami.Theme.highlightColor
        selectedTextColor: Kirigami.Theme.highlightedTextColor
        font.pointSize: Kirigami.Theme.defaultFont.pointSize
        Accessible.name: field.placeholder
        onAccepted: if (field.acceptable) {
            field.accepted();
        }
        Keys.onEscapePressed: event => {
            event.accepted = field.catchesEscape;
            if (field.catchesEscape) {
                field.cancelled();
            }
        }

        Text {
            anchors.verticalCenter: parent.verticalCenter
            visible: input.text.length === 0
            text: field.placeholder
            color: Kirigami.Theme.disabledTextColor
            font: input.font
        }
        HoverHandler {
            cursorShape: Qt.IBeamCursor
        }
    }
    IconButton {
        id: eye
        visible: field.password
        anchors.right: parent.right
        anchors.rightMargin: 4
        anchors.verticalCenter: parent.verticalCenter
        size: 26
        iconName: field.revealed ? "password-show-off" : "password-show-on"
        tip: field.revealed ? qsTr("Hide the password") : qsTr("Show the password")
        onClicked: field.revealed = !field.revealed
    }
}
