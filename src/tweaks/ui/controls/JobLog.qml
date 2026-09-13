/*
    The output of the last long job (a rebuild, an install), tucked away until
    it's wanted; it opens by itself when a job fails.
    SPDX-License-Identifier: GPL-3.0-or-later
*/
import QtQuick
import QtQuick.Controls as QQC2
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

ColumnLayout {
    id: log

    property bool open: false

    Layout.fillWidth: true
    spacing: Kirigami.Units.smallSpacing

    QQC2.ProgressBar {
        Layout.fillWidth: true
        visible: backend.busy
        indeterminate: true
    }

    QQC2.Button {
        Layout.alignment: Qt.AlignRight
        text: log.open ? qsTr("Hide log") : qsTr("Log")
        icon.name: "view-list-text"
        onClicked: log.open = !log.open
    }

    QQC2.TextArea {
        Layout.fillWidth: true
        Layout.preferredHeight: Kirigami.Units.gridUnit * 10
        visible: log.open
        readOnly: true
        font.family: "monospace"
        wrapMode: TextEdit.NoWrap
        text: applicationWindow().jobLog
        onTextChanged: cursorPosition = length
    }

    Connections {
        target: backend
        function onFinished(ok, message) {
            if (!ok) {
                log.open = true;
            }
        }
    }
}
